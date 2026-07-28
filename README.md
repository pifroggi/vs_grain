# Grain Overlay and Generate functions for VapourSynth

<br />

<p align="center">
  <img src="https://raw.githubusercontent.com/pifroggi/vs_grain/refs/heads/main/README_img.png" width="600" />
</p>

## Installation

```
pip install -U vs_grain
```  

> [!TIP]
> For older vapoursynth versions below R74, follow the manual installation steps [here](https://github.com/pifroggi/vs_grain/wiki/Manual-Installation).

<br />

## Generate Realistic Film Grain
Helper function for the very realistic grain generator [fgrain](https://github.com/dnjulek/vapoursynth-zipcu) that animates the grain, adds opacity options, and support for YUV. Grain is only applied to luma. Requires an Nvidia GPU.

```python
import vs_grain
clip = vs_grain.fgrain(clip, iterations=800, size=0.3, deviation=0.0, blur=0.8, opacity=[0.5, 0.5, 0.5], num_streams=1)
```

__*`clip`*__  
Clip to apply grain to.  
Must be in YUV or GRAY format.

__*`iterations`*__  
Higher values look more realistic. Lower values are faster but result in grain that looks less natural.  

__*`size`*__  
Average size of grain particles.  

__*`deviation`*__  
Deviation of size, or how much variation there is in the size of grain particles. High values can cause bad outputs, use with caution.  

__*`blur`*__  
Generates smoother grain.

__*`opacity`*__  
Opacity of generated grain. Can be a list `[0.5, 1.0, 0.5]` for shadows/midtones/highlights, or a single value for everything.

__*`num_streams`*__  
Number of parallel GPU streams. For high end GPUs higher can be a bit faster, but requires more VRAM.

> [!TIP]
> If fgrain is too slow for you, try generating a short grain clip on neutral mid-gray background and then use the overlay function to apply it to the whole clip.

<br />

## Overlay Grain Clip
Bring your own grain clip and overlay it on top of your base clip. This automatically loops the grain clip, crops if too large or stacks if too small.

```python
import vs_grain
clip = vs_grain.overlay(clip, grain, blend_mode="overlay", size=1.0, blur=0.0, opacity=[1.0, 1.0, 1.0], planes=[0, 1, 2])
```

__*`clip`*__  
Clip to apply grain to.  
Must be in YUV or GRAY format.

__*`grain`*__  
Grain clip to overlay. This is expected to be grain on a neutral mid-gray background.  
Must be the same format as the base clip.

__*`blend_mode`*__  
Method used to blend the grain clip with the base clip. Available blend modes:
* `grainshow` Shows the grain without blending.
* `grainmerge` Grain is applied everywhere with the same impact.
* `grainextract` Inverse of grainmerge. Removes grain added via grainmerge.
* `overlay` Grain has strongest impact in midtones and fades toward shadows/highlights.
* `hardlight` Opposite of overlay, meaning grain gets stronger toward shadows/highlights.
* `softlight` Similar to overlay, but dark grains get weaker in shadows and bright grains get weaker in highlights.
* `vividlight` Dark grains get stronger in shadows and bright grains get stronger in highlights. 

<br />

__*`size`*__  
Multiplicator to resize grain clip. Will automatically crop if too large or repeat if too small.

__*`blur`*__  
Smoothes the grain by blurring the grain clip.

__*`opacity`*__  
Opacity of grain clip. Can be a list `[0.5, 1.0, 0.5]` for shadows/midtones/highlights, or a single value for everything.

__*`planes`*__  
Which planes should be affected by the grain clip. Any unmentioned planes will simply be copied.  
If nothing is set, the grain will be applied to all planes.
