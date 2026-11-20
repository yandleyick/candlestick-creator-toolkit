#define UNICODE
#define _UNICODE
#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#define _WIN32_WINNT 0x0A00
#include <windows.h>
#include <windowsx.h>
#include <shellapi.h>
#include <d3d11.h>
#include <dxgi1_6.h>
#include <dcomp.h>
#include <wrl/client.h>
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cwchar>
#include <vector>

using Microsoft::WRL::ComPtr;
constexpr wchar_t ManagerClass[] = L"KonrWings.LG.Manager";
constexpr wchar_t OverlayClass[] = L"KonrWings.LG.Reticle";
constexpr wchar_t PrefKey[] = L"Software\\Konr Wings Overlay";
constexpr UINT TrayMessage=WM_APP+1, FocusChanged=WM_APP+2;
constexpr UINT_PTR DisplayTimer=1, VisibilityTimer=2;
enum Command { Rainbow=101, Black, ToggleStyle, ToggleVisible, Show, Hide, Quit, Menu };

static HWND manager, overlay;
static HINSTANCE instance;
static HICON icon;
static UINT taskbarCreated;
static HWINEVENTHOOK foregroundHook;
static bool black, hidden, hasDisplay, gameActive;
static bool colorKey, visibilityKey;
static const BYTE *art;
static int canvas;
static HMONITOR monitor;
static float brightness=1;
static HRESULT graphicsResult=S_OK;
static ComPtr<ID3D11Device> device;
static ComPtr<ID3D11DeviceContext> context;
static ComPtr<IDXGISwapChain1> swapchain;
static ComPtr<IDCompositionDevice> composition;
static ComPtr<IDCompositionTarget> target;
static ComPtr<IDCompositionVisual> visual;

static void releaseGraphics() {
    visual.Reset(); target.Reset(); composition.Reset(); swapchain.Reset();
    context.Reset(); device.Reset();
}
static BOOL CALLBACK findLG(HMONITOR m,HDC,LPRECT,LPARAM result) {
    MONITORINFOEXW info={}; info.cbSize=sizeof(info);
    if(!GetMonitorInfoW(m,&info)) return TRUE;
    DISPLAY_DEVICEW d={}; d.cb=sizeof(d);
    for(DWORD i=0;EnumDisplayDevicesW(info.szDevice,i,&d,0);i++) {
        if((d.StateFlags & DISPLAY_DEVICE_ACTIVE) && wcsstr(d.DeviceID,L"GSM5CEC")) {
            *reinterpret_cast<HMONITOR*>(result)=m; return FALSE;
        }
    }
    return TRUE;
}

#define TRY_HR(call) do { HRESULT result_=(call); if(FAILED(result_)) return result_; } while(0)
static HRESULT initializeSurface() {
    ComPtr<IDXGIFactory2> factory;
    TRY_HR(CreateDXGIFactory1(IID_PPV_ARGS(factory.GetAddressOf())));
    ComPtr<IDXGIAdapter1> match;
    brightness=1;
    for(UINT a=0;!match;a++) {
        ComPtr<IDXGIAdapter1> adapter;
        if(FAILED(factory->EnumAdapters1(a,adapter.GetAddressOf()))) break;
        for(UINT o=0;;o++) {
            ComPtr<IDXGIOutput> output;
            if(FAILED(adapter->EnumOutputs(o,output.GetAddressOf()))) break;
            DXGI_OUTPUT_DESC od={};
            if(FAILED(output->GetDesc(&od)) || od.Monitor!=monitor) continue;
            match=adapter;
            ComPtr<IDXGIOutput6> advanced;
            DXGI_OUTPUT_DESC1 color={};
            if(SUCCEEDED(output.As(&advanced)) && SUCCEEDED(advanced->GetDesc1(&color)) &&
                color.ColorSpace==DXGI_COLOR_SPACE_RGB_FULL_G2084_NONE_P2020) {
                const float peak=color.MaxLuminance>80?color.MaxLuminance:400.f;
                brightness=std::min(480.f,peak*0.8f)/80.f;
            }
            break;
        }
    }
    if(!match) return DXGI_ERROR_NOT_FOUND;
    TRY_HR(D3D11CreateDevice(match.Get(),D3D_DRIVER_TYPE_UNKNOWN,nullptr,
        D3D11_CREATE_DEVICE_BGRA_SUPPORT,nullptr,0,D3D11_SDK_VERSION,
        device.GetAddressOf(),nullptr,context.GetAddressOf()));
    DXGI_SWAP_CHAIN_DESC1 sd={};
    sd.Width=sd.Height=canvas;
    sd.Format=DXGI_FORMAT_R16G16B16A16_FLOAT;
    sd.SampleDesc.Count=1; sd.BufferUsage=DXGI_USAGE_RENDER_TARGET_OUTPUT;
    sd.BufferCount=2; sd.Scaling=DXGI_SCALING_STRETCH;
    sd.SwapEffect=DXGI_SWAP_EFFECT_FLIP_SEQUENTIAL; sd.AlphaMode=DXGI_ALPHA_MODE_PREMULTIPLIED;
    TRY_HR(factory->CreateSwapChainForComposition(device.Get(),&sd,nullptr,swapchain.GetAddressOf()));
    ComPtr<IDXGIDevice> dxgi;
    TRY_HR(device.As(&dxgi));
    TRY_HR(DCompositionCreateDevice(dxgi.Get(),IID_PPV_ARGS(composition.GetAddressOf())));
    TRY_HR(composition->CreateTargetForHwnd(overlay,TRUE,target.GetAddressOf()));
    TRY_HR(composition->CreateVisual(visual.GetAddressOf()));
    TRY_HR(visual->SetContent(swapchain.Get()));
    TRY_HR(target->SetRoot(visual.Get()));
    return composition->Commit();
}

// All components are non-negative. Sub-half-ULP values can be treated as zero.
static uint16_t toHalf(float x) {
    if(x<0.0000000298023224f) return 0;
    if(x<0.00006103515625f) return (uint16_t)std::lround(x*16777216.f);
    int e=0;
    const float f=std::frexp(x,&e);
    return (uint16_t)(((e+14)<<10)+(int)std::lround((f*2.f-1.f)*1024.f));
}
static HRESULT paintArt(int width) {
    const double physicalScale=width/1920.0;
    double srgb[256];
    for(int i=0;i<256;i++) {
        const double v=i/255.0;
        srgb[i]=v<=0.04045?v/12.92:std::pow((v+0.055)/1.055,2.4);
    }
    std::vector<uint16_t> pixels(canvas*canvas*4);
    const double texelsPerPixel=4.0/physicalScale;
    for(int y=0;y<canvas;y++) for(int x=0;x<canvas;x++) {
        double sum[4]={};
        // Integrate fractional source texels so the arms and dot stay centered at any resolution.
        double xa=(x-canvas/2)*texelsPerPixel+128, ya=(y-canvas/2)*texelsPerPixel+128;
        double xb=xa+texelsPerPixel, yb=ya+texelsPerPixel;
        int lowY=std::max(0,(int)std::floor(ya)), highY=std::min(256,(int)std::ceil(yb));
        int lowX=std::max(0,(int)std::floor(xa)), highX=std::min(256,(int)std::ceil(xb));
        for(int py=lowY;py<highY;py++) for(int px=lowX;px<highX;px++) {
            const BYTE *c=art+4*(py*256+px);
            if(!c[3]) continue;
            double w=(std::min(xb,px+1.0)-std::max(xa,(double)px))*
                     (std::min(yb,py+1.0)-std::max(ya,(double)py))*
                     c[3]/(255.0*texelsPerPixel*texelsPerPixel);
            sum[3]+=w;
            if(!black) for(int k=0;k<3;k++) sum[k]+=srgb[c[k]]*brightness*w;
        }
        for(int k=0;k<4;k++) pixels[(y*canvas+x)*4+k]=toHalf((float)sum[k]);
    }
    ComPtr<ID3D11Texture2D> back;
    TRY_HR(swapchain->GetBuffer(0,IID_PPV_ARGS(back.GetAddressOf())));
    context->UpdateSubresource(back.Get(),0,nullptr,pixels.data(),canvas*8,0);
    TRY_HR(swapchain->Present(0,0));
    return composition->Commit();
}
static void tray(DWORD action) {
    NOTIFYICONDATAW n={}; n.cbSize=sizeof(n); n.hWnd=manager; n.uID=1;
    n.uFlags=NIF_ICON|NIF_MESSAGE|NIF_TIP; n.hIcon=icon; n.uCallbackMessage=TrayMessage;
    const wchar_t* state=!hasDisplay?L"LG disconnected":FAILED(graphicsResult)?L"Display unavailable":
        hidden?L"Hidden":!gameActive?L"Waiting for Overwatch":black?L"Deep Black":brightness>1?L"HDR Rainbow":L"Rainbow";
    swprintf(n.szTip,ARRAYSIZE(n.szTip),L"Konr Wings | %ls",state);
    SetWindowTextW(overlay,n.szTip);
    Shell_NotifyIconW(action,&n);
}

static bool overwatchCenter(POINT& center) {
    HWND window=GetForegroundWindow();
    if(!window || !monitor || IsIconic(window) || !IsWindowVisible(window)) return false;
    DWORD pid=0;
    GetWindowThreadProcessId(window,&pid);
    HANDLE process=OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION,FALSE,pid);
    if(!process) return false;
    wchar_t path[32768];
    DWORD length=ARRAYSIZE(path);
    BOOL found=QueryFullProcessImageNameW(process,0,path,&length);
    CloseHandle(process);
    if(!found) return false;
    const wchar_t* slash=wcsrchr(path,L'\\');
    if(_wcsicmp(slash?slash+1:path,L"Overwatch.exe")!=0) return false;

    RECT client={};
    if(!GetClientRect(window,&client) || client.right<canvas || client.bottom<canvas) return false;
    center={client.right/2,client.bottom/2};
    return ClientToScreen(window,&center) && MonitorFromPoint(center,MONITOR_DEFAULTTONULL)==monitor;
}

static void syncVisibility(bool raiseWindow) {
    POINT center={};
    const bool active=overwatchCenter(center);
    const bool show=active && !hidden && SUCCEEDED(graphicsResult) && visual;
    const bool visible=IsWindowVisible(overlay)!=FALSE;
    if(show) {
        RECT old={};
        GetWindowRect(overlay,&old);
        const int x=center.x-canvas/2, y=center.y-canvas/2;
        if(!visible || raiseWindow || old.left!=x || old.top!=y || old.right-old.left!=canvas)
            SetWindowPos(overlay,HWND_TOPMOST,x,y,canvas,canvas,SWP_NOACTIVATE|SWP_SHOWWINDOW);
    } else if(visible) {
        ShowWindow(overlay,SW_HIDE);
    }
    if(gameActive!=active) {
        gameActive=active;
        tray(NIM_MODIFY);
    }
}
static void refresh(bool rebuild) {
    HMONITOR found=nullptr;
    EnumDisplayMonitors(nullptr,nullptr,findLG,(LPARAM)&found);
    hasDisplay=found!=nullptr;
    if(!found) {
        ShowWindow(overlay,SW_HIDE); releaseGraphics(); monitor=nullptr; gameActive=false; tray(NIM_MODIFY); return;
    }
    MONITORINFO info={sizeof(info)};
    GetMonitorInfoW(found,&info);
    const RECT r=info.rcMonitor;
    const int width=r.right-r.left;
    const int side=2*(int)std::ceil(32.*width/1920.);
    rebuild=rebuild||found!=monitor||canvas!=side||!visual;
    monitor=found; canvas=side;
    if(rebuild) {
        releaseGraphics();
        graphicsResult=initializeSurface();
    }
    if(SUCCEEDED(graphicsResult)) graphicsResult=paintArt(width);
    syncVisibility(true);
    tray(NIM_MODIFY);
}
static void menu() {
    HMENU m=CreatePopupMenu();
    AppendMenuW(m,MF_STRING,LONG(Rainbow),brightness>1?L"HDR Rainbow":L"Rainbow");
    AppendMenuW(m,MF_STRING,LONG(Black),L"Deep Black");
    CheckMenuRadioItem(m,Rainbow,Black,black?Black:Rainbow,MF_BYCOMMAND);
    AppendMenuW(m,MF_SEPARATOR,0,nullptr);
    AppendMenuW(m,MF_STRING,ToggleStyle,colorKey?L"Switch color\tCtrl+Alt+W":L"Switch color");
    AppendMenuW(m,MF_STRING,ToggleVisible,
        hidden?(visibilityKey?L"Show wings\tCtrl+Alt+H":L"Show wings"):
               (visibilityKey?L"Hide wings\tCtrl+Alt+H":L"Hide wings"));
    AppendMenuW(m,MF_SEPARATOR,0,nullptr); AppendMenuW(m,MF_STRING,Quit,L"Exit");
    POINT p; GetCursorPos(&p); SetForegroundWindow(manager);
    int choice=TrackPopupMenu(m,TPM_RETURNCMD|TPM_RIGHTBUTTON,p.x,p.y,0,manager,nullptr);
    DestroyMenu(m); PostMessageW(manager,WM_NULL,0,0);
    if(choice) PostMessageW(manager,WM_COMMAND,choice,0);
}
static void command(UINT c) {
    if(c==Quit) { DestroyWindow(manager); return; }
    if(c==Menu) { menu(); return; }
    if(c==ToggleVisible) hidden=!hidden;
    if(c==Hide) hidden=true;
    if(c==Show) hidden=false;
    if(c==Black||c==Rainbow||c==ToggleStyle) {
        black=c==ToggleStyle?!black:c==Black; hidden=false;
        DWORD b=black; RegSetKeyValueW(HKEY_CURRENT_USER,PrefKey,L"Black",REG_DWORD,&b,sizeof b);
    }
    refresh(false);
}
static void CALLBACK foreground(HWINEVENTHOOK,DWORD,HWND,LONG,LONG,DWORD,DWORD) {
    if(manager) PostMessageW(manager,FocusChanged,0,0);
}
static LRESULT CALLBACK managerProc(HWND hwnd,UINT msg,WPARAM w,LPARAM l) {
    if(msg==taskbarCreated && taskbarCreated) { tray(NIM_ADD); return 0; }
    switch(msg) {
    case WM_COMMAND: command(LOWORD(w)); return 0;
    case WM_HOTKEY: command((UINT)w); return 0;
    case WM_DISPLAYCHANGE: case WM_SETTINGCHANGE: case WM_DEVICECHANGE:
        SetTimer(hwnd,DisplayTimer,400,nullptr); return 0;
    case WM_TIMER:
        if(w==DisplayTimer) { KillTimer(hwnd,DisplayTimer); refresh(true); }
        else if(w==VisibilityTimer) syncVisibility(false);
        return 0;
    case FocusChanged:
        syncVisibility(true);
        return 0;
    case TrayMessage:
        if(l==WM_RBUTTONUP||l==WM_LBUTTONUP||l==WM_CONTEXTMENU) menu(); return 0;
    case WM_DESTROY:
        if(foregroundHook) UnhookWinEvent(foregroundHook);
        UnregisterHotKey(hwnd,ToggleStyle); UnregisterHotKey(hwnd,ToggleVisible);
        tray(NIM_DELETE); PostQuitMessage(0); return 0;
    }
    return DefWindowProcW(hwnd,msg,w,l);
}
static LRESULT CALLBACK overlayProc(HWND hwnd,UINT msg,WPARAM w,LPARAM l) {
    if(msg==WM_NCHITTEST) return HTTRANSPARENT;
    if(msg==WM_MOUSEACTIVATE) return MA_NOACTIVATE;
    if(msg==WM_ERASEBKGND) return 1;
    return DefWindowProcW(hwnd,msg,w,l);
}
static UINT parse(const wchar_t* s) {
    if(!wcscmp(s,L"--rainbow")) return Rainbow;
    if(!wcscmp(s,L"--black")) return Black;
    if(!wcscmp(s,L"--show")) return Show;
    if(!wcscmp(s,L"--hide")) return Hide;
    if(!wcscmp(s,L"--exit")) return Quit;
    return Menu;
}
int WINAPI wWinMain(HINSTANCE h,HINSTANCE,LPWSTR args,int) {
    instance=h;
    SetProcessDpiAwarenessContext(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2);
    HANDLE single=CreateMutexW(nullptr,FALSE,L"Local\\KonrWings.LG.Overlay");
    if(!single) return 2;
    const UINT requested=parse(args);
    if(GetLastError()==ERROR_ALREADY_EXISTS) {
        for(int i=0;i<50;i++) {
            HWND existing=FindWindowW(ManagerClass,nullptr);
            if(existing){ PostMessageW(existing,WM_COMMAND,requested,0); break; }
            Sleep(20);
        }
        CloseHandle(single); return 0;
    }
    if(requested==Quit){ CloseHandle(single); return 0; }
    CoInitializeEx(nullptr,COINIT_APARTMENTTHREADED);
    HRSRC res=FindResourceW(h,MAKEINTRESOURCEW(101),RT_RCDATA);
    if(!res||SizeofResource(h,res)!=256*256*4) return 3;
    art=(const BYTE*)LockResource(LoadResource(h,res));
    DWORD b=0,len=sizeof(b);
    if(RegGetValueW(HKEY_CURRENT_USER,PrefKey,L"Black",RRF_RT_REG_DWORD,nullptr,&b,&len)==ERROR_SUCCESS) black=b!=0;
    icon=LoadIconW(h,MAKEINTRESOURCEW(102)); taskbarCreated=RegisterWindowMessageW(L"TaskbarCreated");
    WNDCLASSW wc={}; wc.hInstance=h; wc.lpfnWndProc=managerProc; wc.lpszClassName=ManagerClass;
    if(!RegisterClassW(&wc)) return 4;
    wc.lpfnWndProc=overlayProc; wc.lpszClassName=OverlayClass;
    if(!RegisterClassW(&wc)) return 5;
    manager=CreateWindowExW(WS_EX_TOOLWINDOW,ManagerClass,L"Konr Wings controls",WS_POPUP,0,0,1,1,nullptr,nullptr,h,nullptr);
    overlay=CreateWindowExW(WS_EX_TOPMOST|WS_EX_TOOLWINDOW|WS_EX_NOACTIVATE|WS_EX_TRANSPARENT|
        WS_EX_LAYERED|WS_EX_NOREDIRECTIONBITMAP,OverlayClass,L"Konr Wings",WS_POPUP,0,0,1,1,nullptr,nullptr,h,nullptr);
    if(!manager||!overlay) return 6;
    SetLayeredWindowAttributes(overlay,0,255,LWA_ALPHA);
    tray(NIM_ADD);
    colorKey=RegisterHotKey(manager,ToggleStyle,MOD_CONTROL|MOD_ALT|MOD_NOREPEAT,'W')!=0;
    visibilityKey=RegisterHotKey(manager,ToggleVisible,MOD_CONTROL|MOD_ALT|MOD_NOREPEAT,'H')!=0;
    foregroundHook=SetWinEventHook(EVENT_SYSTEM_FOREGROUND,EVENT_SYSTEM_FOREGROUND,nullptr,foreground,0,0,
        WINEVENT_OUTOFCONTEXT);
    SetTimer(manager,VisibilityTimer,750,nullptr);
    if(requested==Menu) refresh(true); else command(requested);
    MSG msg;
    while(GetMessageW(&msg,nullptr,0,0)>0) { TranslateMessage(&msg); DispatchMessageW(&msg); }
    releaseGraphics(); DestroyWindow(overlay); CoUninitialize(); CloseHandle(single);
    return 0;
}
