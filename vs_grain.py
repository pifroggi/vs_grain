
# Script by pifroggi https://github.com/pifroggi/vs_grain
# or tepete and pifroggi on Discord

import vapoursynth as vs

core = vs.core

def _opacitymask(luma, opacity_dark, opacity_mid, opacity_bright, peak=1.0):
    thresh1, thresh2, thresh3, thresh4 = 0.176, 0.333, 0.549, 0.784
    span1 = (thresh2 - thresh1) * peak
    span2 = (thresh4 - thresh3) * peak
    ramp1 = f"x {thresh1 * peak} - {span1} / 0 max 1 min {opacity_mid * peak}   {opacity_dark * peak} - * {opacity_dark * peak} +"
    ramp2 = f"x {thresh3 * peak} - {span2} / 0 max 1 min {opacity_bright * peak} {opacity_mid * peak} - * {opacity_mid * peak}  +"
    return core.std.Expr(luma, expr=f"x {thresh2 * peak} < {ramp1} x {thresh3 * peak} < {opacity_mid * peak} {ramp2} ? ?")

def _maskedmerge(clipa, clipb, mask, planes):
    # makes maskedmerge work on half float formats
    clipa_format = clipa.format
    clipa_planes = clipa_format.num_planes
    if clipa_format.sample_type == vs.FLOAT and clipa_format.bits_per_sample == 16:
        planes_selected = [i in planes for i in range(clipa_planes)]
        if clipa_planes > 1:
            if mask.format.color_family == vs.GRAY and (clipa_format.subsampling_w or clipa_format.subsampling_h):
                mask_sub = core.resize.Point(mask, width=clipa.width  >> clipa_format.subsampling_w, height=clipa.height >> clipa_format.subsampling_h)
                mask = core.std.ShufflePlanes([mask, mask_sub, mask_sub], planes=[0, 0, 0], colorfamily=clipa_format.color_family)
            else:
                mask = core.std.ShufflePlanes(mask, planes=[0] * clipa_planes, colorfamily=clipa_format.color_family)
        expr = ["x 1 z - * y z * +" if selected else "" for selected in planes_selected]
        return core.akarin.Expr([clipa, clipb, mask], expr=expr)
    return core.std.MaskedMerge(clipa, clipb, mask, planes=planes)


def fgrain(clip, iterations=800, size=0.3, deviation=0.0, blur=0.8, opacity=0.5):
    
    # checks
    if not isinstance(clip, vs.VideoNode):
        raise TypeError("vs_grain.fgrain: Clip must be a vapoursynth clip.")
    if clip.format.id  == vs.PresetVideoFormat.NONE or clip.width  == 0 or clip.height  == 0:
        raise TypeError("vs_grain.fgrain: Clip must have constant format and dimensions.")
    if clip.format.color_family not in (vs.YUV, vs.GRAY):
        raise ValueError("vs_grain.fgrain: Clip must be in YUV or GRAY format.")
    if not isinstance(iterations, int) or isinstance(iterations, bool):
        raise TypeError("vs_grain.fgrain: Number of iterations must be an integer.")
    if iterations < 1:
        raise ValueError("vs_grain.fgrain: Number of iterations must be at least 1.")
    if size <= 0:
        raise ValueError("vs_grain.fgrain: Grain size must be larger than 0.")
    if deviation < 0:
        raise ValueError("vs_grain.fgrain: Grain deviation can not be negative.")
    if blur < 0:
        raise ValueError("vs_grain.fgrain: Blur strength can not be negative.")
    if isinstance(opacity, (list, tuple)):
        if len(opacity) != 3:
            raise ValueError("vs_grain.fgrain: Opacity must be a single value, or a list for [shadows, midtones, highlights].")
        opacity_dark,  opacity_mid,  opacity_bright = map(float, opacity)
    else:
        opacity_dark = opacity_mid = opacity_bright = float(opacity)
    if not all(0.0 <= x <= 1.0 for x in (opacity_dark, opacity_mid, opacity_bright)):
        raise ValueError("vs_grain.fgrain: Opacity values must be in the 0-1 range.")
    if opacity_dark == opacity_mid == opacity_bright == 0.0:
        return clip
    
    # get luma plane
    luma = clip
    if clip.format.color_family == vs.YUV:
        luma = core.std.ShufflePlanes(luma, 0, vs.GRAY)
    
    # convert to float
    luma_format = luma.format.id
    if luma.format.id != vs.GRAYS:
        luma = core.resize.Point(luma, format=vs.GRAYS)
    
    # generate grain
    luma_grain = core.akarin.PropExpr(luma, lambda: dict(FGRAIN_SEED_OFFSET="N width *"))
    luma_grain = core.fgrain_cuda.Add(luma_grain, num_iterations=iterations, grain_radius_mean=size, grain_radius_std=deviation, sigma=blur)
    
    # merge grain
    if (opacity_dark == opacity_mid == opacity_bright):
        luma_grain = core.std.Merge(luma, luma_grain, weight=opacity_dark)
    else:
        mask = _opacitymask(luma, opacity_dark, opacity_mid, opacity_bright, peak=1.0)
        luma_grain = core.std.MaskedMerge(luma, luma_grain, mask)
    
    # convert back
    if luma_grain.format.id != luma_format:
        luma_grain = core.resize.Point(luma_grain, format=luma_format)
    
    # merge
    if clip.format.color_family == vs.YUV:
        return core.std.ShufflePlanes(clips=[luma_grain, clip, clip], planes=[0, 1, 2], colorfamily=vs.YUV, prop_src=clip)
    return luma_grain


def overlay(clip, grain, blend_mode="overlay", size=1.0, blur=0, opacity=1.0, planes=None):

    # checks
    if not isinstance(clip, vs.VideoNode):
        raise TypeError("vs_grain.overlay: Clip must be a vapoursynth clip.")
    if not isinstance(grain, vs.VideoNode):
        raise TypeError("vs_grain.overlay: Grain must be a vapoursynth clip.")
    if clip.format.id  == vs.PresetVideoFormat.NONE or clip.width  == 0 or clip.height  == 0:
        raise TypeError("vs_grain.overlay: Clip must have constant format and dimensions.")
    if grain.format.id == vs.PresetVideoFormat.NONE or grain.width == 0 or grain.height == 0:
        raise TypeError("vs_grain.overlay: Grain must have constant format and dimensions.")
    if clip.format.color_family  not in (vs.YUV, vs.GRAY):
        raise ValueError("vs_grain.overlay: Clip must be in YUV or GRAY format.")
    if grain.format.color_family not in (vs.YUV, vs.GRAY):
        raise ValueError("vs_grain.overlay: Grain must be in YUV or GRAY format.")
    if clip.format.id != grain.format.id:
        raise ValueError("vs_grain.overlay: Base clip and grain clip must have the same format.")
    if not (0.1 <= size <= 10.0):
        raise ValueError("vs_grain.overlay: Size factor must be in the 0.1-10.0 range with 1.0 meaning no resizing.")
    if not isinstance(blur, int) or isinstance(blur, bool):
        raise TypeError("vs_grain.overlay: Blur strength must be an integer.")
    if blur < 0:
        raise ValueError("vs_grain.overlay: Blur strength can not be negative.")
    if isinstance(opacity, (list, tuple)):
        if len(opacity) != 3:
            raise ValueError("vs_grain.overlay: Opacity must be a single value, or a list for [shadows, midtones, highlights].")
        opacity_dark,  opacity_mid,  opacity_bright = map(float, opacity)
        uniform_opacity = False
    else:
        opacity_dark = opacity_mid = opacity_bright = float(opacity)
        uniform_opacity = True
    if not all(0.0 <= x <= 1.0 for x in (opacity_dark, opacity_mid, opacity_bright)):
        raise ValueError("vs_grain.overlay: Opacity values must be in the 0-1 range.")
    num_planes = clip.format.num_planes
    if planes is None:
        planes = list(range(num_planes))
    if isinstance(planes, int):
        planes = [planes]
    if num_planes == 1:
        planes = [0]
    if any(p < 0 or p >= num_planes for p in planes):
        raise ValueError("vs_grain.overlay: Invalid plane index specified.")
    if opacity_dark == opacity_mid == opacity_bright == 0.0:
        return clip
    
    sub_w = 1 << clip.format.subsampling_w
    sub_h = 1 << clip.format.subsampling_h
    
    # set peaks
    int_format = clip.format.sample_type == vs.INTEGER
    neutral    = (1 << (clip.format.bits_per_sample - 1)) if int_format else 0.5
    peak       = ((1 << clip.format.bits_per_sample) - 1) if int_format else 1.0
    factor     = (1 << clip.format.bits_per_sample)       if int_format else 1.0
    neutrals   = [neutral] * num_planes
    peaks      = [peak]    * num_planes
    factors    = [factor]  * num_planes
    
    # resize grain
    if size != 1.0:
        new_w = max(sub_w, (round(grain.width  * size) // sub_w) * sub_w)
        new_h = max(sub_h, (round(grain.height * size) // sub_h) * sub_h)
        grain = core.resize.Bilinear(grain, width=new_w, height=new_h)
    
    # stack grain if too small
    stack_h = -(-clip.width  // grain.width)
    stack_v = -(-clip.height // grain.height)
    if stack_h > 1:
        grain = core.std.StackHorizontal([grain] * stack_h)
    if stack_v > 1:
        grain = core.std.StackVertical([grain]   * stack_v)
    
    # crop stacked grain to clip dimensions
    crop_w = grain.width  - clip.width
    crop_h = grain.height - clip.height
    if crop_w or crop_h:
        left  = (crop_w // 2) // sub_w * sub_w
        top   = (crop_h // 2) // sub_h * sub_h
        grain = core.std.CropAbs(grain, left=left, top=top, width=clip.width, height=clip.height)
    
    # blur grain
    if blur != 0:
        grain = core.resize.Bilinear(grain, width=grain.width * 4, height=grain.height * 4)
        if blur > 1:
            grain = core.std.BoxBlur(grain, hradius=blur - 1, vradius=blur - 1, hpasses=2, vpasses=2)
        grain = core.resize.Bilinear(grain, width=grain.width // 4, height=grain.height // 4)
    
    # loop grain to match clip
    grain = core.std.Loop(grain, times=-(-clip.num_frames // grain.num_frames))[:clip.num_frames]
    
    # blend modes exprs based on "havsfunc" https://github.com/HomeOfVapourSynthEvolution/havsfunc
    blend_exprs = {
        "grainshow":      "{Y}",
        "grainmerge":     "{X} {Y} + {neutral} -",
        "grainextract":   "{X} {Y} - {neutral} +",
        "overlay":        "{X} {neutral} < 2 {X} {Y} * {peak} / * {peak} 2 {peak} {X} - {peak} {Y} - * {peak} / * - ?",
        "hardlight":      "{Y} {neutral} < 2 {Y} {X} * {peak} / * {peak} 2 {peak} {Y} - {peak} {X} - * {peak} / * - ?",
        "softlight":      "{Y} {neutral} > {X} {peak} {X} - {Y} {neutral} - * {neutral} / 0.5 {X} {neutral} - abs {peak} / - * + {X} {X} {neutral} {Y} - {neutral} / * 0.5 {X} {neutral} - abs {peak} / - * - ? 2 * {X} -",
        "vividlight":     "{Y} {neutral} < {Y} 0 <= 2 {Y} * {peak} {peak} {X} - {factor} * 2 {Y} * / - ? 2 {Y} {neutral} - * {peak} >= 2 {Y} {neutral} - * {X} {factor} * {peak} 2 {Y} {neutral} - * - / ? ?",
    }
    try:
        blend_expr = blend_exprs[blend_mode]
    except KeyError:
        raise KeyError("vs_grain.overlay: Invalid blend mode specified.")

    # build exprs for each plane
    exprs = [""] * num_planes        # set all planes to "" which means fast plane copy
    for plane in range(num_planes):  # loop trough planes and set appropriate expr
        if plane not in planes:      # don't add expr if plane is not selected
            continue

        # when clip is YUV and float, shift UV planes into 0-1 range
        if (clip.format.color_family == vs.YUV and clip.format.sample_type == vs.FLOAT) and plane in (1, 2):
            pre   = f"x 0.5 + xs! y 0.5 + ys!"  # shift both inputs up and store
            main  = blend_expr.format(X="xs@", Y="ys@", neutral=neutrals[plane], peak=peaks[plane], factor=factors[plane])
            post  = "0.5 -"                     # shift result back down
            blend = f"{pre} {main} {post}"
        # for normal planes just use x and y directly
        else:
            blend = blend_expr.format(X="x",   Y="y",   neutral=neutrals[plane], peak=peaks[plane], factor=factors[plane])

        # if opacity is uniform, merge directly with the expression
        if uniform_opacity:
            exprs[plane] = f"x {blend} x - {opacity_mid} * +"
        else:
            exprs[plane] = blend

    # merge grain onto clip with build exprs
    grain = core.akarin.Expr([clip, grain], expr=exprs)
    if uniform_opacity:
        return grain

    # build opacity mask
    mask = clip
    if clip.format.color_family == vs.YUV:
        mask = core.std.ShufflePlanes(mask, 0, vs.GRAY)
    mask = _opacitymask(mask, opacity_dark, opacity_mid, opacity_bright, peak)

    # merge grain onto clip
    return _maskedmerge(clip, grain, mask, planes=planes)
