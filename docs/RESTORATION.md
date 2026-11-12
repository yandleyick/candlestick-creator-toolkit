# Restoration and export

The local workflows have used Real-ESRGAN, NAFNet, Restormer, RIFE (Vulkan and PyTorch variants), OpenCV, and FFmpeg. The tool catalog links to their owning projects. Their source/model licenses remain separate. Download model weights into a local `models/` directory, not Git.

Start with short representative samples: skin, hair, fast hands, text, dark regions, motion blur, compression, and cut boundaries. Compare the untreated source, the earlier acceptable baseline, and each proposed change. Preserve a softer baseline. Stronger sharpening or restoration is not inherently better; reject waxy skin, invented texture, halos, smeared motion, and temporal flicker.

`scripts/restore_frames.py` ports the bounded luminance-recovery step from the Natural v3 workflow. It processes a directory of 8-bit or 16-bit PNG frames into a new directory and preserves their dimensions and bit depth. It does not run a neural model, perform optical-flow interpolation, infer HDR, or reproduce the original scene-specific color fit.

```powershell
python scripts/restore_frames.py jobs/source-frames --out jobs/gentle-frames --mode gentle
```

Real-ESRGAN is an optional upscaling stage. NAFNet/Restormer were deblur experiments; an available model or technically valid export is not evidence of visual approval. RIFE produces intermediate frames rather than recovering frames captured by the original camera. Prevent interpolation across scene cuts and inspect occlusions, weapon/HUD motion, and thin detail.

For an image-sequence workflow, record frame count, first-frame number, frame rate as an exact rational value, color encoding, and source audio offset. Keep the source audio independently and account for its timing when remuxing. Do not use a frame-sequence example blindly with variable-frame-rate input.

The original Natural v3 delivery used a calibrated color fit and separate SDR and HDR10 outputs. Its LUTs and mastering metadata were scene-specific. Do not apply those LUTs or mastering values to new footage. SDR-to-HDR conversion is an authored HDR rendition; metadata alone does not create captured HDR detail. The general clip exporter intentionally accepts SDR only.

Technical validation should include full decode, frame rate/count, duration, audio streams, dimensions, color primaries/transfer/matrix, and hashes. Also compare audio content and timing against the intended source. Visual and listening review remain separate. A platform preview may still be processing or limited in resolution; verify the downloaded final file when evaluating native-resolution quality.
