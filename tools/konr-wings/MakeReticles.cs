using System;
using System.Drawing;
using System.Drawing.Drawing2D;
using System.Drawing.Imaging;
using System.IO;

class MakeReticles {
    // Coordinates in reference-screen pixels, measured from the green aiming dot.
    static GraphicsPath Wing() {
        var p = new GraphicsPath();
        p.StartFigure();
        p.AddBezier(-5.15f,-8.1f, -4.8f,-10.4f, -10.9f,-15.8f, -15.55f,-15.8f);
        p.AddBezier(-15.55f,-15.8f, -21.4f,-15.8f, -25.15f,-8.0f, -25.15f,0);
        p.AddBezier(-25.15f,0, -25.15f,8.0f, -22.2f,16.05f, -16.0f,16.05f);
        p.AddBezier(-16.0f,16.05f, -11.6f,16.05f, -5.0f,11.1f, -5.1f,8.0f);
        p.AddBezier(-5.1f,8.0f, -6.0f,7.25f, -11.4f,13.25f, -15.6f,13.25f);
        p.AddBezier(-15.6f,13.25f, -20.1f,13.25f, -22.25f,7.0f, -22.25f,0);
        p.AddBezier(-22.25f,0, -22.25f,-6.7f, -19.4f,-13.0f, -15.45f,-13.0f);
        p.AddBezier(-15.45f,-13.0f, -11.4f,-13.0f, -6.0f,-7.2f, -5.15f,-8.1f);
        p.CloseFigure();
        return p;
    }

    static readonly double[] Angles = {-2.65,-1.62,-0.36,0.68,1.73,2.65};
    static readonly int[] Left = {0xffbd48,0x3bffae,0x18faff,0x55ffbc,0xf3ff35,0xff8744};
    static readonly int[] Right = {0xff7956,0xff43b8,0xa880ff,0xdca6ff,0xff74df,0xff43ad};

    static Color Rainbow(double x, double y) {
        if (Math.Abs(x)<3) return Color.FromArgb(95,255,58);
        double angle = Math.Atan2(y/14.4,(Math.Abs(x)-15.45)/8.3);
        int i=0;
        while(i<Angles.Length-2 && angle>Angles[i+1]) ++i;
        double t=Math.Max(0,Math.Min(1,(angle-Angles[i])/(Angles[i+1]-Angles[i])));
        int[] stops=x<0 ? Left : Right;
        int a=stops[i], b=stops[i+1];
        Func<int,int> component=shift=>(int)Math.Round(((a>>shift)&255)*(1-t)+((b>>shift)&255)*t);
        return Color.FromArgb(component(16),component(8),component(0));
    }

    // Produce a transparent icon from the geometry using area coverage at pixel edges.
    static void Render(int side, double pixelsPerRefPixel, string output, string texture) {
        const int aa=8;
        using(var mask=new Bitmap(side*aa,side*aa,PixelFormat.Format32bppArgb))
        using(var g=Graphics.FromImage(mask))
        using(var p=Wing())
        using(var reflected=(GraphicsPath)p.Clone())
        using(var reflect=new Matrix(-1,0,0,1,0,0))
        using(var rainbow=new Bitmap(side,side,PixelFormat.Format32bppArgb))
        using(var black=new Bitmap(side,side,PixelFormat.Format32bppArgb)) {
            g.SmoothingMode=SmoothingMode.None;
            float scale=(float)(aa*pixelsPerRefPixel);
            using(var tr=new Matrix(scale,0,0,scale,side*aa/2f,side*aa/2f)) g.Transform=tr;
            reflected.Transform(reflect);
            g.FillPath(Brushes.White,p); g.FillPath(Brushes.White,reflected);
            g.FillEllipse(Brushes.White,-1.95f,-1.95f,3.9f,3.9f);
            g.Flush();
            var bytes=new byte[side*side*4];
            var rect=new Rectangle(0,0,mask.Width,mask.Height);
            var data=mask.LockBits(rect,ImageLockMode.ReadOnly,PixelFormat.Format32bppArgb);
            var alpha=new byte[data.Stride*mask.Height];
            System.Runtime.InteropServices.Marshal.Copy(data.Scan0,alpha,0,alpha.Length);
            mask.UnlockBits(data);
            for(int y=0;y<side;++y) for(int x=0;x<side;++x) {
                int sum=0;
                for(int sy=0;sy<aa;++sy) for(int sx=0;sx<aa;++sx)
                    sum+=alpha[(y*aa+sy)*data.Stride+(x*aa+sx)*4+3];
                int coverage=(sum+aa*aa/2)/(aa*aa);
                if(coverage==0) continue;
                Color c=Rainbow((x+0.5-side/2.0)/pixelsPerRefPixel,(y+0.5-side/2.0)/pixelsPerRefPixel);
                rainbow.SetPixel(x,y,Color.FromArgb(coverage,c));
                black.SetPixel(x,y,Color.FromArgb(coverage,0,0,0));
                int n=(y*side+x)*4;
                bytes[n]=c.R; bytes[n+1]=c.G; bytes[n+2]=c.B; bytes[n+3]=(byte)coverage;
            }
            if(texture!=null) File.WriteAllBytes(texture,bytes);
            if(output!=null) {
                rainbow.Save(Path.Combine(output,"Konr Wings - Rainbow.png"),ImageFormat.Png);
                black.Save(Path.Combine(output,"Konr Wings - Deep Black.png"),ImageFormat.Png);
            }
        }
    }
    static void Main(string[] args) {
        const double reticleScale = 0.70;
        Render(256,4 * reticleScale,null,args[0]);
        Render(96,(4.0/3.0) * reticleScale,args[1],null);
    }
}
