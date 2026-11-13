"""Pure fitted-glass surface; no Blender or scene mutations.

Use actual 3D rim measurements as the Dirichlet boundary for a smooth
mean-value-coordinate correction of the prior shallow-curvature surface.
All inputs/outputs are in normalized Tripo coordinates (working scene is 5x).
"""
import math
import numpy as np


def build_surface(ring, pane):
    ring = np.asarray(ring, dtype=float)
    rim_a = ring[:, [0, 2]]
    rim_b = np.roll(rim_a, -1, axis=0)
    rim_e = rim_b - rim_a
    rim_l2 = np.einsum('ij,ij->i', rim_e, rim_e)
    rim_y0 = ring[:, 1]
    rim_dy = np.roll(rim_y0, -1) - rim_y0
    z0 = float(ring[:, 2].min())
    dz = float(np.ptp(ring[:, 2]))
    width = float(np.abs(ring[:, 0]).max())
    t = (ring[:, 2] - z0) / dz
    matrix = np.column_stack((np.ones(len(ring)), t, t*t, (ring[:, 0]/width)**2))
    coeff = np.linalg.lstsq(matrix, ring[:, 1], rcond=None)[0]

    def base(x, z):
        q = (z-z0)/dz
        return float(coeff @ np.array([1., q, q*q, (x/width)**2])) + .00065 - .0007*max(0., 1.-(x/width)**2)*max(0., 4*q*(1-q))

    def rim_depth(x, z):
        p = np.array([x, z])
        u = np.clip(np.einsum('ij,ij->i', p-rim_a, rim_e)/np.maximum(rim_l2, 1e-30), 0., 1.)
        nearest = rim_a + u[:, None]*rim_e
        j = int(np.argmin(np.einsum('ij,ij->i', nearest-p, nearest-p)))
        return float(rim_y0[j] + u[j]*rim_dy[j])

    def target(x, z):
        return rim_depth(x, z) + .00065

    # Include every original pane vertex; interpolate along each segment.
    # No duplicate boundary points, including the repeated closing point.
    raw = [tuple(p) for p in pane.exterior.coords[:-1]]
    cleaned = []
    for p in raw:
        if not cleaned or math.dist(p, cleaned[-1]) > 1e-11:
            cleaned.append(p)
    if math.dist(cleaned[0], cleaned[-1]) < 1e-11:
        cleaned.pop()
    points = []
    for a, b in zip(cleaned, cleaned[1:]+cleaned[:1]):
        count = max(1, int(math.ceil(math.dist(a, b)/.0008)))
        points.extend((a[0]+(b[0]-a[0])*i/count, a[1]+(b[1]-a[1])*i/count) for i in range(count))
    points = np.asarray(points, dtype=float)
    delta = np.array([target(x, z)-base(x, z) for x, z in points])
    edges = np.roll(points, -1, axis=0)-points
    edge_l2 = np.einsum('ij,ij->i', edges, edges)

    def correction(x, z):
        p = np.array([x, z])
        r = points-p
        d = np.sqrt(np.einsum('ij,ij->i', r, r))
        if float(d.min()) < 1e-10:
            return target(x, z)-base(x, z)
        u = np.clip(-np.einsum('ij,ij->i', r, edges)/np.maximum(edge_l2, 1e-30), 0., 1.)
        nearest = r + u[:, None]*edges
        dist2 = np.einsum('ij,ij->i', nearest, nearest)
        if float(dist2.min()) < 1e-18:
            return target(x, z)-base(x, z)
        rn = np.roll(r, -1, axis=0)
        cross = r[:, 0]*rn[:, 1]-r[:, 1]*rn[:, 0]
        denom = d*np.roll(d, -1)+np.einsum('ij,ij->i', r, rn)
        # The near-collinear case is handled above; retain signs outside the pane
        # to give the caller a short, continuous extrapolation for normal probes.
        denom = np.where(np.abs(denom) < 1e-24, np.copysign(1e-24, denom+1e-30), denom)
        tan_half = cross/denom
        weights = (np.roll(tan_half, 1)+tan_half)/d
        total = float(weights.sum())
        if not math.isfinite(total) or abs(total) < 1e-15:
            return target(x, z)-base(x, z)
        return float(weights @ delta / total)

    cx, cz = float(pane.centroid.x), float(pane.centroid.y)
    minx, minz, maxx, maxz = pane.bounds
    rx, rz = .38*(maxx-minx), .25*(maxz-minz)
    centre_correction = correction(cx, cz)

    def surface(x, z):
        x, z = float(x), float(z)
        rho2 = ((x-cx)/rx)**2 + ((z-cz)/rz)**2
        # C2 compact support, fully within the pane. It preserves the previous
        # centre exactly without changing the measured boundary fit.
        anchor = max(0., 1.-rho2)**3
        value = base(x, z)+correction(x, z)-centre_correction*anchor
        if not math.isfinite(value):
            raise ValueError('Nonfinite fitted windscreen depth')
        return value

    samples = [pane.exterior.interpolate(pane.exterior.length*i/1024) for i in range(1024)]
    errors = [abs(surface(p.x, p.y)-target(p.x, p.y)) for p in samples]
    diagnostics = {
        'method': 'mean-value boundary correction with C2 compact interior centre anchor',
        'boundary_target': 'nearest actual retained 3D lip Y + 0.00065 raw inward',
        'boundary_nodes': len(points),
        'boundary_samples': len(samples),
        'maximum_boundary_target_error_raw': max(errors),
        'maximum_boundary_target_error_mm_at_5x': max(errors)*5000.,
        'centre_anchor_xz_raw': [cx, cz],
        'centre_Y_change_raw': surface(cx, cz)-base(cx, cz),
        'unanchored_centre_correction_raw': centre_correction,
        'boundary_correction_range_raw': [float(delta.min()), float(delta.max())],
        'note': 'Numerical boundary fit is not visual acceptance. Review both pillars at grazing angles and lit glass reflections.'
    }
    return surface, diagnostics


def build_fair_surface(ring, pane):
    """Low-order fair pane for use WITH local depth fairing of the body lip.

    Unlike build_surface, this deliberately does not interpolate every damaged
    source rim point. Callers must fit the adjacent lip/seal to this same surface.
    The immutable XZ outline supplies width; a robust biquadratic fit supplies Y.
    """
    ring = np.asarray(ring, dtype=float)
    width = float(np.abs(ring[:, 0]).max())
    zmid = float((ring[:, 2].min()+ring[:, 2].max())/2)
    zhalf = float(np.ptp(ring[:, 2])/2)
    def basis(x, z):
        u, v = x/width, (z-zmid)/zhalf
        return np.array([1., u, v, u*u, u*v, v*v, u*u*v, u*v*v, u*u*v*v])
    # Arc-weighted samples prevent dense corner triangles from dominating.
    points = []
    for a, b in zip(ring, np.roll(ring, -1, axis=0)):
        count = max(1, int(math.ceil(float(np.linalg.norm((b-a)[[0,2]]))/.004)))
        points.extend(a+(b-a)*j/count for j in range(count))
    points = np.asarray(points)
    rim_matrix = np.array([basis(p[0], p[2]) for p in points])
    rim_targets = points[:, 1] + .00065
    # Weak centreline anchors preserve the earlier shallow bow while allowing
    # measured pillar/header depths to determine the overall rake and curvature.
    z0 = float(ring[:,2].min()); dz = 2*zhalf
    t = (ring[:,2]-z0)/dz
    oldc = np.linalg.lstsq(np.column_stack((np.ones(len(ring)), t, t*t, (ring[:,0]/width)**2)), ring[:,1], rcond=None)[0]
    anchors=[]; anchor_y=[]
    for z in np.linspace(z0+.02, z0+dz-.02, 7):
        for x in [-.07, 0., .07]:
            q=(z-z0)/dz
            anchors.append(basis(x,z))
            anchor_y.append(float(oldc @ np.array([1.,q,q*q,(x/width)**2]))+.00065-.0007*max(0.,1-(x/width)**2)*max(0.,4*q*(1-q)))
    anchor_matrix=np.array(anchors);anchor_y=np.array(anchor_y)
    # Huber IRLS reduces the influence of Tripo's isolated depth-fold vertices.
    weights=np.ones(len(points)); ridge=np.diag([0.,0.,0.,0.,0.,0.,.2,.2,.35])
    coeff=np.zeros(9)
    for iteration in range(12):
        w=np.sqrt(weights)
        matrix=np.vstack((rim_matrix*w[:,None],anchor_matrix*.28,ridge))
        values=np.concatenate((rim_targets*w,anchor_y*.28,np.zeros(9)))
        coeff=np.linalg.lstsq(matrix,values,rcond=None)[0]
        residual=rim_matrix@coeff-rim_targets
        weights=np.minimum(1.,.0015/np.maximum(np.abs(residual),1e-15))
    def surface(x,z):
        return float(basis(float(x),float(z))@coeff)
    changes=np.array([surface(p[0],p[2])-.00065-p[1] for p in ring])
    sample_changes=rim_matrix@coeff-rim_targets
    worst=int(np.argmax(np.abs(changes)))
    dense_rim=[]; dense_rim_tapered=[]; chord_errors=[]
    for a,b in zip(ring,np.roll(ring,-1,axis=0)):
        count=max(1,int(math.ceil(float(np.linalg.norm((b-a)[[0,2]]))/.002)))
        ya=surface(a[0],a[2])-.00065;yb=surface(b[0],b[2])-.00065
        for j in range(count):
            t=j/count;p=a+(b-a)*t;y=surface(p[0],p[2])-.00065
            dense_rim.append([float(p[0]),y,float(p[2])])
            u=max(0.,min(1.,(float(p[2])-.311)/.010));weight=u*u*(3-2*u)
            dense_rim_tapered.append([float(p[0]),float(p[1]+weight*(y-p[1])),float(p[2])])
            chord_errors.append(abs(y-(ya+t*(yb-ya))))
    normals=[];bow=[]
    for z in np.linspace(z0,z0+dz,21):
        v=(z-zmid)/zhalf
        bow.append(float(coeff[3]+coeff[6]*v+coeff[8]*v*v))
        for x in np.linspace(-width,width,21):
            u=x/width
            dx=(coeff[1]+2*coeff[3]*u+coeff[4]*v+2*coeff[6]*u*v+coeff[7]*v*v+2*coeff[8]*u*v*v)/width
            dzv=(coeff[2]+coeff[4]*u+2*coeff[5]*v+coeff[6]*u*u+2*coeff[7]*u*v+2*coeff[8]*u*u*v)/zhalf
            normals.append((float(dx),float(dzv)))
    diagnostics={
        'method':'robust low-order biquadratic pane; adjacent lip must be locally faired to this shared surface',
        'basis':'1,u,v,u²,uv,v²,u²v,uv²,u²v²; normalized X and Z',
        'coefficients':coeff.tolist(),'x_scale_raw':width,'z_center_raw':zmid,'z_scale_raw':zhalf,
        'rim_depth_target_offset_raw':.00065,
        'required_lip_depth_displacement_mm_at_5x':{
            'maximum_source_vertex':float(np.abs(changes).max()*5000),
            'median_dense_boundary':float(np.median(np.abs(sample_changes))*5000),
            'p95_dense_boundary':float(np.quantile(np.abs(sample_changes),.95)*5000),
            'worst_source_coordinate_raw':ring[worst].tolist(),
            'worst_signed_Y_change_raw':float(changes[worst])},
        'source_vertex_depth_changes_raw':changes.tolist(),
        'maximum_fair_surface_to_original_edge_chord_error_mm_at_5x':float(max(chord_errors)*5000),
        'dense_fair_rim_raw':dense_rim,
        'dense_rim_with_original_lower_sill_depth_raw':dense_rim_tapered,
        'dense_rim_note':'Station spacing <= .002 raw. Full fair rim is Y(surface)-.00065; alternative tapers depth edits from zero at Z=.311 to full at Z=.321 to retain lower cowl return. New boundary stations require matching body-edge subdivision, not standalone bridging across unmatched long edges.',
        'horizontal_bow_coefficient_range_raw':[min(bow),max(bow)],
        'derivative_ranges':{'dy_dx':[min(n[0] for n in normals),max(n[0] for n in normals)],'dy_dz':[min(n[1] for n in normals),max(n[1] for n in normals)]},
        'note':'A fair glass surface, not an exact source-depth fit. Review reflections and both pillar joints after local depth fairing; do not report numeric fit as visual acceptance.'
    }
    return surface, diagnostics
