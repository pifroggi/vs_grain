import vapoursynth as vs
import functools
core = vs.core

def fgrain(clip, iterations, size, deviation, blur_strength, opacity):
    #checks
    if clip.format.id not in (vs.YUV444PS, vs.GRAYS):
        raise ValueError("Clip must be in YUV444PS or GRAYS format.")
    
    if clip.format.id == vs.YUV444PS:
        clipY = core.std.ShufflePlanes(clip, planes=0, colorfamily=vs.GRAY)
    else:
        clipY = clip

    #animate
    def animator(n):
        return core.fgrain_cuda.Add(clipY, num_iterations=iterations, grain_radius_mean=size,
                                    grain_radius_std=deviation, sigma=blur_strength, seed=n * clipY.width)
    clipYgrain = core.std.FrameEval(clipY, functools.partial(animator))
    clipYgrain = core.std.Merge(clipY, clipYgrain, weight=opacity)

    if clip.format.id == vs.YUV444PS:
        #for YUV444PS, merge back the color planes
        clip = core.std.ShufflePlanes(clips=[clipYgrain, clip, clip], planes=[0, 1, 2], colorfamily=vs.YUV)
    else:
        #for GRAYS, simply return the processed grayscale clip
        clip = clipYgrain
    return clip

#blend modes function from "havsfunc" https://github.com/HomeOfVapourSynthEvolution/havsfunc
def haf_Overlay(base, overlay, opacity=1.0, mode='normal'):

    #set neutral and peak values based on whether base clip uses integer or floating point sample type
    if base.format.sample_type == vs.INTEGER:
        neutral = 1 << (base.format.bits_per_sample - 1)
        peak = (1 << base.format.bits_per_sample) - 1
        factor = 1 << base.format.bits_per_sample
    else:
        neutral = 0.5
        peak = factor = 1.0

    #upscale base to full chroma resolution if it uses subsampling
    if base.format.subsampling_w > 0 or base.format.subsampling_h > 0:
        base_orig = base
        base = base.resize.Point(format=base.format.replace(subsampling_w=0, subsampling_h=0))
    else:
        base_orig = None

    #blend modes
    mode = mode.lower()
    if mode == 'normal':
        pass
    elif mode == 'average':
        expr = f'x y + 2 /'
    elif mode == 'grainextract':
        expr = f'x y - {neutral} +'
    elif mode == 'grainmerge':
        expr = f'x y + {neutral} -'
    elif mode == 'hardlight':
        expr = f'y {neutral} < 2 y x * {peak} / * {peak} 2 {peak} y - {peak} x - * {peak} / * - ?'
    elif mode == 'linearlight':
        expr = f'y {neutral} < y 2 x * + {peak} - y 2 x {neutral} - * + ?'
    elif mode == 'overlay':
        expr = f'x {neutral} < 2 x y * {peak} / * {peak} 2 {peak} x - {peak} y - * {peak} / * - ?'
    elif mode == 'softlight':
        expr = f'x {neutral} > y {peak} y - x {neutral} - * {neutral} / 0.5 y {neutral} - abs {peak} / - * + y y {neutral} x - {neutral} / * 0.5 y {neutral} - abs {peak} / - * - ?'
    elif mode == 'vividlight':
        expr = f'x {neutral} < x 0 <= 2 x * {peak} {peak} y - {factor} * 2 x * / - ? 2 x {neutral} - * {peak} >= 2 x {neutral} - * y {factor} * {peak} 2 x {neutral} - * - / ? ?'
    else:
        raise vs.Error("Overlay: invalid 'mode' specified")
    if mode != 'normal':
        overlay = core.std.Expr([overlay, base], expr=[expr] * base.format.num_planes)

    #merge overlay onto base clip
    last = core.std.Merge(base, overlay, weight=opacity)
    
    #resize to original format if base was upsampled
    if base_orig is not None:
        last = last.resize.Point(format=base_orig.format)
    return last

def overlay(clip, grain, size=1.0, blend_mode='overlay', blur_strength=0, opacity=1.0):

    #checks
    if clip.format.color_family != vs.YUV or grain.format.color_family != vs.YUV:
        raise ValueError("Both clips must be in YUV format.")
    if clip.format.id != grain.format.id:
        raise ValueError("Both clips must have the same format.")

    #resize grain
    grain = core.resize.Bilinear(grain, width=int(grain.width*size), height=int(grain.height*size))

    #stack grain if too small
    clip_width = clip.width
    clip_height = clip.height
    grain_width = grain.width
    grain_height = grain.height
    stack_horizontal = (clip_width + grain_width - 1) // grain_width
    stack_vertical = (clip_height + grain_height - 1) // grain_height
    if stack_horizontal > 1:
        grain = core.std.StackHorizontal([grain] * stack_horizontal)
    if stack_vertical > 1:
        grain = core.std.StackVertical([grain] * stack_vertical)

    #crop stacked grain to match clip dimensions
    grain_width = grain.width
    grain_height = grain.height
    crop_left = (grain_width - clip_width) // 2
    crop_top = (grain_height - clip_height) // 2
    crop_right = grain_width - clip_width - crop_left
    crop_bottom = grain_height - clip_height - crop_top
    grain = core.std.Crop(grain, left=crop_left, top=crop_top, right=crop_right, bottom=crop_bottom)
    
    #blur
    if blur_strength != 0:
        grain = core.resize.Bilinear(grain, width=grain.width*4, height=grain.height*4)
        if blur_strength > 1:
            grain = core.std.BoxBlur(grain, hradius = blur_strength-1, vradius = blur_strength-1, hpasses = 2, vpasses = 2)
        grain = core.resize.Bilinear(grain, width=grain.width/4, height=grain.height/4)

    #calculate the number of times grain needs to be looped
    clip_duration = clip.num_frames
    grain_duration = grain.num_frames
    loops_required = clip_duration // grain_duration
    grain = core.std.Loop(grain, times=loops_required)

    #if looped grain is shorter than clip, append extra frames to match the length
    remaining_frames = clip_duration - grain.num_frames
    if remaining_frames > 0:
        extra_grain = grain[0:remaining_frames]
        grain = core.std.Splice([grain, extra_grain])

    #overlay grain onto clip
    return haf_Overlay(base=clip, overlay=grain, mode=blend_mode, opacity=opacity)