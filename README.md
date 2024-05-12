# Grain Overlay and Generate functions for Vapoursynth

### Requirements
* [vs-fgrain-cuda](https://github.com/AmusementClub/vs-fgrain-cuda) (optional, not needed for overlay)

## Generate Realistic Film Grain
Very simple wrapper function for [fgrain](https://github.com/AmusementClub/vs-fgrain-cuda) that animates the grain, adds opacity option, and support for YUV. Requires an Nvidia GPU.

    import vs_grain
    clip = vs_grain.fgrain(clip, iterations=800, size=0.5, deviation=0.0, blur_strength=0.9, opacity=0.1)

__*clip*__  
Clip to apply grain to.  
Must be in YUV444PS or GRAYS format.

__*iterations*__  
Higher values look more realistic. Lower values speed up the processing time but result in grain that looks less natural.  
Originally called "num_iterations" in fgrain.

__*size*__  
Average size of the grain particles.  
Originally called "grain_radius_mean" in fgrain.

__*deviation*__  
Standard deviation of size, which dictates how much variation there is in the size of the grain particles.  
Originally called "grain_radius_std" in fgrain.

__*blur_strength*__  
Produces smoother grain. This is not really a blur, but it has a similar effect.  
Originally called "sigma" in fgrain.

__*opacity*__  
Opacity of grain.

## Overlay Grain Clip
Set your own grain clip and overlay it on top of your base clip. This automatically loops the grain clip, crops it if it is too large and repeats it if it is too small.

    import vs_grain
    clip = vs_grain.overlay(clip, grain, blend_mode='overlay', size=1.0, blur_strength=0, opacity=1.0)

__*clip*__  
Clip to apply grain to.  
Must be in YUV format.

__*grain*__  
Grain clip to overlay.  
Must be in YUV format.

__*size*__  
Multiplicator to resize grain clip. Will automatically crop if too large or repeat if too small.

__*blur_strength*__  
Produces smoother grain by blurring the grain clip.

__*opacity*__  
Opacity of grain.

__*blend_mode*__  
Method used to blend the grain clip with the base clip. Blend function is from [havsfunc](https://github.com/HomeOfVapourSynthEvolution/havsfunc) by HolyWu.  
Available blend modes:
* overlay
* hardlight
* linearlight
* softlight
* vividlight
* grainmerge
* grainextract
* average
* normal

## Tips
If fgrain is too slow for you, try generating a short grain clip with it on gray background and then loop and add it with overlay. That looks a little less good, but is much faster.
