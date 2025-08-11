# gear_draw.py
# Requires: pip install drawsvg
import math
import drawsvg as ds

def rotate(x, y, ang):
    c = math.cos(ang)
    s = math.sin(ang)
    return x*c - y*s, x*s + y*c

def involute_points(base_r, r_start, r_end, n=30):
    """
    return list of (x,y) for involute starting at radius r_start up to r_end
    param t ranges from t_start..t_end where r = base_r*sqrt(1+t^2)
    involute param eqns: x = rb*(cos t + t*sin t), y = rb*(sin t - t*cos t)
    """
    if r_end <= base_r:
        return []
    # t = sqrt((r/rb)^2 - 1)
    t_start = math.sqrt(max(0.0, (r_start/base_r)**2 - 1.0))
    t_end   = math.sqrt(max(0.0, (r_end/base_r)**2 - 1.0))
    pts = []
    for i in range(n+1):
        t = t_start + (t_end - t_start) * i / n
        x = base_r * (math.cos(t) + t * math.sin(t))
        y = base_r * (math.sin(t) - t * math.cos(t))
        pts.append((x, y))
    return pts

def gear_path_points(z, m, pressure_angle_deg=20.0,
                     addendum=None, dedendum=None,
                     tooth_involute_points=30, top_arc_points=8, root_arc_points=6):
    """
    Build coordinates (x,y) for a single tooth polygon (CCW) centered on x-axis.
    Returns a list of polygons (one per tooth after rotation will be used externally).
    """
    # geometry
    pressure_angle = math.radians(pressure_angle_deg)
    pitch_r = m * z / 2.0
    addendum = m if addendum is None else addendum
    dedendum = 1.25*m if dedendum is None else dedendum
    outer_r = pitch_r + addendum
    root_r  = max(0.1*m, pitch_r - dedendum)  # avoid negative or zero root radius
    base_r  = pitch_r * math.cos(pressure_angle)

    # angular measures
    circular_pitch = 2 * math.pi / z      # angle per tooth (full)
    tooth_thickness_linear = math.pi * m / 2.0  # at pitch circle (standard)
    half_tooth_angle_at_pitch = (tooth_thickness_linear / pitch_r) / 2.0

    # involute param values and alpha at pitch circle (to align involute)
    # compute involute point at pitch circle (if base_r < pitch_r)
    if base_r < pitch_r:
        t_p = math.sqrt((pitch_r/base_r)**2 - 1.0)
        # involute point at pitch circle:
        x_p = base_r * (math.cos(t_p) + t_p * math.sin(t_p))
        y_p = base_r * (math.sin(t_p) - t_p * math.cos(t_p))
        alpha_p = math.atan2(y_p, x_p)
    else:
        # no involute (pressure_angle too small relative to gear geometry)
        alpha_p = 0.0
        t_p = 0.0

    # We want the involute point at the pitch circle to be located at +half_tooth_angle_at_pitch
    rotation = half_tooth_angle_at_pitch - alpha_p

    # generate one flank (right flank), compute involute points from base_r -> outer_r
    if base_r < outer_r:
        inv_pts = involute_points(base_r, max(base_r, base_r), outer_r, n=tooth_involute_points)
    else:
        inv_pts = []

    # rotate the involute into place and translate as needed
    right_flank = [rotate(x, y, rotation) for (x, y) in inv_pts]

    # mirror left flank about x-axis (i.e. reflect y -> -y) and then rotate by -rotation accordingly
    left_flank = [ (x, -y) for (x,y) in right_flank ]
    # Note: left_flank needs to be reversed when building polygon order.

    # outer arc between left and right flank endpoints
    if right_flank:
        p_out_r = right_flank[-1]
        p_out_l = left_flank[-1]
        ang_r = math.atan2(p_out_r[1], p_out_r[0])
        ang_l = math.atan2(p_out_l[1], p_out_l[0])
    else:
        # fallback: place arcs centered around tooth centerline
        ang_r = rotation
        ang_l = -rotation

    # ensure arc goes the shorter way across the top of the tooth:
    # want to move from left flank angle (larger negative) to right flank (positive),
    # so create angles from ang_l -> ang_r via increasing angles.
    # build top arc points on outer_r
    top_arc = []
    # if ang_l > ang_r, adjust ang_r to be > ang_l by adding 2*pi when necessary
    if ang_r < ang_l:
        ang_r += 2*math.pi
    for i in range(top_arc_points+1):
        t = ang_l + (ang_r - ang_l) * i / top_arc_points
        top_arc.append( (outer_r * math.cos(t), outer_r * math.sin(t)) )

    # root arc between right & left root points (on dedendum circle)
    # choose root points at ± half tooth pitch angle (space between teeth)
    half_space = circular_pitch / 2.0
    # set the root flank angles a bit inside the half spacing
    root_angle_r = half_space * 0.6
    root_angle_l = -half_space * 0.6
    root_arc = []
    # go from right root angle to left root angle (clockwise around root circle)
    # ensure continuity: if root_angle_l < root_angle_r, we wrap
    if root_angle_l < root_angle_r:
        root_angle_l += 2*math.pi
    for i in range(root_arc_points+1):
        t = root_angle_r + (root_angle_l - root_angle_r) * i / root_arc_points
        root_arc.append( (root_r * math.cos(t), root_r * math.sin(t)) )

    # Build polygon: start at right root, go along right flank from base->outer, top arc, left flank back to base, root arc
    # Need to get right flank from base outward: the involute_points return from base->outer
    # but right_flank may be empty (degenerate); handle gracefully
    pts = []
    # right root
    pts.append(root_arc[0])
    # right flank: from base to outer (only points with radius >= base_r)
    if right_flank:
        # we want to start from the point on the base circle - approximate by projecting the first involute point radially
        # then add full list
        pts.extend(right_flank)
    else:
        # no involute case - go straight to top arc start
        pass

    # top arc leftwards
    pts.extend(top_arc)
    # left flank: mirrored but go from outer->base (reverse)
    if left_flank:
        pts.extend(reversed(left_flank))
    # root arc closing back to right_root
    pts.extend(root_arc)
    return pts, pitch_r, outer_r, root_r, base_r

def draw_gear(z=24, m=2.0, pressure_angle_deg=20.0, filename='gear.svg',
              stroke_width=0.8, fill_color='#dfe7f3'):
    # build one tooth
    tooth_pts, pitch_r, outer_r, root_r, base_r = gear_path_points(z, m, pressure_angle_deg)

    # flatten and rotate each tooth around the gear center
    drawing_size = (outer_r + 5*m) * 2.0
    dwg = ds.Drawing(drawing_size, drawing_size, origin=( -drawing_size/2.0, -drawing_size/2.0))
    # optional guides
    dwg.append(ds.Circle(0,0,pitch_r, stroke_width=0.5, stroke='gray', fill='none'))
    dwg.append(ds.Circle(0,0,outer_r, stroke_width=0.3, stroke='gray', fill='none'))
    dwg.append(ds.Circle(0,0,root_r, stroke_width=0.3, stroke='gray', fill='none'))

    # path for a single tooth: convert pts to flat list for Lines (close it)
    single_tooth_coords = []
    for (x,y) in tooth_pts:
        single_tooth_coords.append(x)
        single_tooth_coords.append(y)

    # place z teeth by rotating the single tooth around center
    angle_step = 2*math.pi / z
    for i in range(z):
        ang = i * angle_step
        # rotate every point by ang
        tooth_coords = []
        for j in range(0, len(single_tooth_coords), 2):
            x = single_tooth_coords[j]
            y = single_tooth_coords[j+1]
            xr, yr = rotate(x, y, ang)
            tooth_coords.append(xr)
            tooth_coords.append(yr)
        # draw as polygon (Lines with close=True)
        lines = ds.Lines(*tooth_coords, close=True, fill=fill_color, stroke='black', stroke_width=stroke_width)
        dwg.append(lines)

    # draw center hole
    hole_r = max(0.3*m, m*z*0.02)
    dwg.append(ds.Circle(0,0,hole_r, fill='white', stroke='black', stroke_width=0.6))

    # optional: draw axes
    dwg.append(ds.Line(-drawing_size/2,0,drawing_size/2,0, stroke='black', stroke_width=0.2, stroke_dasharray='2,2'))
    dwg.append(ds.Line(0,-drawing_size/2,0,drawing_size/2, stroke='black', stroke_width=0.2, stroke_dasharray='2,2'))

    # save
    dwg.set_pixel_scale(4)  # improve resolution when exporting to PNG if needed
    dwg.save_svg(filename)
    print(f"Saved gear SVG to: {filename}")
    return filename

if __name__ == '__main__':
    # Example usage:
    # - z = number of teeth
    # - m = module (mm per tooth)
    # The drawing origin is centered, saved to gear.svg
    draw_gear(z=36, m=2.0, pressure_angle_deg=20.0, filename='gear.svg')
