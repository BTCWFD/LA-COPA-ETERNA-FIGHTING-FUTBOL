/* ============================================================================
   LA COPA ETERNA: SANGRE Y POTRERO — SELF-CONTAINED WEBGL2 glTF 2.0 (.glb) VIEWER
   Zero external CDN dependencies • 100% offline-capable on localhost:8080
   Supports binary .glb parsing, GPU skinning (JOINTS_0 / WEIGHTS_0 / IBM),
   STEP/LINEAR keyframe animation playback, Renacimiento Sfumato vs Street-Ink
   shaders, Wireframe/Skeleton Overlay, Chaos Cloth Heatmap, and Orbit Camera.
   ============================================================================ */
(function (global) {
  'use strict';

  // --------------------------------------------------------------------------
  // Minimal Column-Major Mat4 & Quaternion Math (Zero External Dependencies)
  // --------------------------------------------------------------------------
  function mat4Identity(out = new Float32Array(16)) {
    out.fill(0);
    out[0] = 1; out[5] = 1; out[10] = 1; out[15] = 1;
    return out;
  }

  function mat4Multiply(out, a, b) {
    const a00 = a[0], a01 = a[1], a02 = a[2], a03 = a[3];
    const a10 = a[4], a11 = a[5], a12 = a[6], a13 = a[7];
    const a20 = a[8], a21 = a[9], a22 = a[10], a23 = a[11];
    const a30 = a[12], a31 = a[13], a32 = a[14], a33 = a[15];

    for (let c = 0; c < 4; c++) {
      const o = c * 4;
      const b0 = b[o], b1 = b[o + 1], b2 = b[o + 2], b3 = b[o + 3];
      out[o]     = a00 * b0 + a10 * b1 + a20 * b2 + a30 * b3;
      out[o + 1] = a01 * b0 + a11 * b1 + a21 * b2 + a31 * b3;
      out[o + 2] = a02 * b0 + a12 * b1 + a22 * b2 + a32 * b3;
      out[o + 3] = a03 * b0 + a13 * b1 + a23 * b2 + a33 * b3;
    }
    return out;
  }

  function mat4FromTRS(out, t, q, s) {
    const x = q[0], y = q[1], z = q[2], w = q[3];
    const x2 = x + x, y2 = y + y, z2 = z + z;
    const xx = x * x2, xy = x * y2, xz = x * z2;
    const yy = y * y2, yz = y * z2, zz = z * z2;
    const wx = w * x2, wy = w * y2, wz = w * z2;
    const sx = s[0], sy = s[1], sz = s[2];

    out[0] = (1 - (yy + zz)) * sx;
    out[1] = (xy + wz) * sx;
    out[2] = (xz - wy) * sx;
    out[3] = 0;

    out[4] = (xy - wz) * sy;
    out[5] = (1 - (xx + zz)) * sy;
    out[6] = (yz + wx) * sy;
    out[7] = 0;

    out[8] = (xz + wy) * sz;
    out[9] = (yz - wx) * sz;
    out[10] = (1 - (xx + yy)) * sz;
    out[11] = 0;

    out[12] = t[0];
    out[13] = t[1];
    out[14] = t[2];
    out[15] = 1;
    return out;
  }

  function mat4Perspective(out, fovyRad, aspect, near, far) {
    const f = 1.0 / Math.tan(fovyRad * 0.5);
    const nf = 1.0 / (near - far);
    out.fill(0);
    out[0] = f / aspect;
    out[5] = f;
    out[10] = (far + near) * nf;
    out[11] = -1;
    out[14] = 2 * far * near * nf;
    return out;
  }

  function mat4LookAt(out, eye, target, up) {
    let zx = eye[0] - target[0];
    let zy = eye[1] - target[1];
    let zz = eye[2] - target[2];
    let len = Math.hypot(zx, zy, zz) || 1;
    zx /= len; zy /= len; zz /= len;

    let xx = up[1] * zz - up[2] * zy;
    let xy = up[2] * zx - up[0] * zz;
    let xz = up[0] * zy - up[1] * zx;
    len = Math.hypot(xx, xy, xz) || 1;
    xx /= len; xy /= len; xz /= len;

    const yx = zy * xz - zz * xy;
    const yy = zz * xx - zx * xz;
    const yz = zx * xy - zy * xx;

    out[0] = xx; out[4] = xy; out[8]  = xz; out[12] = -(xx * eye[0] + xy * eye[1] + xz * eye[2]);
    out[1] = yx; out[5] = yy; out[9]  = yz; out[13] = -(yx * eye[0] + yy * eye[1] + yz * eye[2]);
    out[2] = zx; out[6] = zy; out[10] = zz; out[14] = -(zx * eye[0] + zy * eye[1] + zz * eye[2]);
    out[3] = 0;  out[7] = 0;  out[11] = 0;  out[15] = 1;
    return out;
  }

  function quatSlerp(out, a, b, t) {
    let ax = a[0], ay = a[1], az = a[2], aw = a[3];
    let bx = b[0], by = b[1], bz = b[2], bw = b[3];
    let dot = ax * bx + ay * by + az * bz + aw * bw;
    if (dot < 0) {
      dot = -dot;
      bx = -bx; by = -by; bz = -bz; bw = -bw;
    }
    if (dot > 0.9995) {
      out[0] = ax + t * (bx - ax);
      out[1] = ay + t * (by - ay);
      out[2] = az + t * (bz - az);
      out[3] = aw + t * (bw - aw);
    } else {
      const theta0 = Math.acos(Math.min(1, Math.max(-1, dot)));
      const theta = theta0 * t;
      const sinTheta = Math.sin(theta);
      const sinTheta0 = Math.sin(theta0);
      const s0 = Math.cos(theta) - dot * sinTheta / sinTheta0;
      const s1 = sinTheta / sinTheta0;
      out[0] = s0 * ax + s1 * bx;
      out[1] = s0 * ay + s1 * by;
      out[2] = s0 * az + s1 * bz;
      out[3] = s0 * aw + s1 * bw;
    }
    const n = Math.hypot(out[0], out[1], out[2], out[3]) || 1;
    out[0] /= n; out[1] /= n; out[2] /= n; out[3] /= n;
    return out;
  }

  // --------------------------------------------------------------------------
  // Binary glTF 2.0 (.glb) Parser
  // --------------------------------------------------------------------------
  const GLTF_TYPE_COMPONENTS = {
    SCALAR: 1,
    VEC2: 2,
    VEC3: 3,
    VEC4: 4,
    MAT2: 4,
    MAT3: 9,
    MAT4: 16
  };

  function getTypedArrayConstructor(componentType) {
    switch (componentType) {
      case 5120: return Int8Array;
      case 5121: return Uint8Array;
      case 5122: return Int16Array;
      case 5123: return Uint16Array;
      case 5125: return Uint32Array;
      case 5126: return Float32Array;
      default: return Float32Array;
    }
  }

  function readAccessor(gltf, binBuffer, accessorIdx) {
    const acc = gltf.accessors[accessorIdx];
    const bv = gltf.bufferViews[acc.bufferView || 0];
    const numComp = GLTF_TYPE_COMPONENTS[acc.type] || 1;
    const TypedCtor = getTypedArrayConstructor(acc.componentType);
    const compSize = TypedCtor.BYTES_PER_ELEMENT;
    const baseOffset = (bv.byteOffset || 0) + (acc.byteOffset || 0);
    const stride = bv.byteStride || (numComp * compSize);

    if (stride === numComp * compSize) {
      return new TypedCtor(binBuffer.buffer, binBuffer.byteOffset + baseOffset, acc.count * numComp);
    }

    const out = new TypedCtor(acc.count * numComp);
    const dv = new DataView(binBuffer.buffer, binBuffer.byteOffset);
    for (let i = 0; i < acc.count; i++) {
      const elemOffset = baseOffset + i * stride;
      for (let c = 0; c < numComp; c++) {
        const off = elemOffset + c * compSize;
        if (acc.componentType === 5126) out[i * numComp + c] = dv.getFloat32(off, true);
        else if (acc.componentType === 5123) out[i * numComp + c] = dv.getUint16(off, true);
        else if (acc.componentType === 5125) out[i * numComp + c] = dv.getUint32(off, true);
        else if (acc.componentType === 5121) out[i * numComp + c] = dv.getUint8(off);
        else if (acc.componentType === 5122) out[i * numComp + c] = dv.getInt16(off, true);
        else out[i * numComp + c] = dv.getInt8(off);
      }
    }
    return out;
  }

  function parseGLB(arrayBuffer) {
    const dv = new DataView(arrayBuffer);
    if (arrayBuffer.byteLength < 20) throw new Error('GLB too small');
    const magic = dv.getUint32(0, true);
    const version = dv.getUint32(4, true);
    if (magic !== 0x46546c67 || version !== 2) {
      throw new Error('Invalid glTF 2.0 binary header');
    }

    let offset = 12;
    let gltf = null;
    let binBuffer = new Uint8Array(0);
    const totalLen = dv.getUint32(8, true);

    while (offset < totalLen) {
      const chunkLen = dv.getUint32(offset, true);
      const chunkType = dv.getUint32(offset + 4, true);
      const chunkStart = offset + 8;
      if (chunkType === 0x4e4f534a) {
        const jsonBytes = new Uint8Array(arrayBuffer, chunkStart, chunkLen);
        gltf = JSON.parse(new TextDecoder('utf-8').decode(jsonBytes));
      } else if (chunkType === 0x004e4942) {
        binBuffer = new Uint8Array(arrayBuffer, chunkStart, chunkLen);
      }
      offset = chunkStart + chunkLen;
    }

    if (!gltf) throw new Error('GLB missing JSON chunk');
    return { gltf, binBuffer };
  }

  // --------------------------------------------------------------------------
  // Shaders (WebGL2 GLSL ES 3.00)
  // --------------------------------------------------------------------------
  const MESH_VERT_SRC = `#version 300 es
  precision highp float;

  layout(location = 0) in vec3 aPosition;
  layout(location = 1) in vec3 aNormal;
  layout(location = 2) in vec4 aColor;
  layout(location = 3) in vec4 aJoints;
  layout(location = 4) in vec4 aWeights;
  layout(location = 5) in vec2 aUv;

  uniform mat4 uModel;
  uniform mat4 uView;
  uniform mat4 uProj;
  uniform int uHasSkin;
  uniform mat4 uJointMatrices[64];
  uniform int uRenderMode; // 0: SHADED, 1: SKELETON, 2: CLOTH, 3: SMEAR
  uniform float uWindPct;
  uniform float uTime;
  uniform float uSmearScale;
  uniform int uPrimIndex;

  out vec3 vWorldPos;
  out vec3 vNormal;
  out vec4 vColor;
  out vec3 vLocalPos;
  out vec2 vUv;

  void main() {
    vec4 pos = vec4(aPosition, 1.0);
    vec3 norm = aNormal;

    if (uHasSkin == 1) {
      ivec4 j = ivec4(aJoints);
      float wSum = aWeights.x + aWeights.y + aWeights.z + aWeights.w;
      if (wSum > 0.0001) {
        vec4 w = aWeights / wSum;
        mat4 skinMat =
          w.x * uJointMatrices[clamp(j.x, 0, 63)] +
          w.y * uJointMatrices[clamp(j.y, 0, 63)] +
          w.z * uJointMatrices[clamp(j.z, 0, 63)] +
          w.w * uJointMatrices[clamp(j.w, 0, 63)];
        pos = skinMat * pos;
        norm = mat3(skinMat) * norm;
      }
    }

    // Subtle Chaos Cloth vertex flutter in CLOTH or SHADED mode on kit primitive
    if ((uRenderMode == 2 || uRenderMode == 0) && uHasSkin == 1 && uPrimIndex == 1 && uWindPct > 0.01) {
      float hemFactor = clamp((1.35 - pos.y) * 0.9, 0.0, 1.0);
      float wave = sin(uTime * 5.2 + pos.x * 7.0 + pos.z * 5.0) * 0.022 * uWindPct * hemFactor;
      pos.x += wave;
      pos.z += wave * 0.6;
    }

    // Control Rig Smear exaggeration on active striking forward reach in SMEAR mode
    if (uRenderMode == 3 && uHasSkin == 1 && uSmearScale > 1.01) {
      float forwardExt = max(0.0, pos.z - 0.12);
      pos.z += forwardExt * (uSmearScale - 1.0) * 0.55;
    }

    vec4 world = uModel * pos;
    vWorldPos = world.xyz;
    vNormal = normalize(mat3(uModel) * norm);
    vColor = aColor;
    vLocalPos = pos.xyz;
    vUv = aUv;
    gl_Position = uProj * uView * world;
  }`;

  const MESH_FRAG_SRC = `#version 300 es
  precision highp float;

  in vec3 vWorldPos;
  in vec3 vNormal;
  in vec4 vColor;
  in vec3 vLocalPos;
  in vec2 vUv;

  uniform vec3 uCameraPos;
  uniform vec4 uBaseColor;
  uniform vec3 uEmissive;
  uniform float uMetallic;
  uniform float uRoughness;
  uniform int uHasVertexColor;
  uniform sampler2D uBaseColorTex;
  uniform int uHasBaseColorTex;
  uniform int uLightingMode; // 0: SFUMATO, 1: STREET_INK
  uniform int uRenderMode;   // 0: SHADED, 1: SKELETON, 2: CLOTH, 3: SMEAR
  uniform int uHasSkin;
  uniform float uModelHeight;

  out vec4 fragColor;

  vec3 clothHeatmap(float t) {
    // 0.0 (cyan pinned) -> 0.5 (emerald/gold) -> 1.0 (crimson free)
    vec3 cPin = vec3(0.0, 0.90, 1.0);
    vec3 cMid = vec3(0.96, 0.77, 0.32);
    vec3 cFree = vec3(1.0, 0.16, 0.33);
    if (t < 0.5) return mix(cPin, cMid, t * 2.0);
    return mix(cMid, cFree, (t - 0.5) * 2.0);
  }

  void main() {
    vec3 N = normalize(vNormal);
    vec3 V = normalize(uCameraPos - vWorldPos);
    float ndotv = max(dot(N, V), 0.0);

    vec4 texSample = uHasBaseColorTex == 1 ? texture(uBaseColorTex, vUv) : vec4(1.0);
    // Skinned fighters store Chaos Cloth weights in COLOR_0 ([cw, 0.85, 0.15, 1.0]);
    // never tint albedo with COLOR_0 when textured or skinned.
    bool useVertColForAlbedo = (uHasVertexColor == 1) && (uHasBaseColorTex == 0) && (uHasSkin == 0);
    vec4 vertCol = useVertColForAlbedo ? vColor : vec4(1.0);
    vec3 albedo = uBaseColor.rgb * texSample.rgb * vertCol.rgb;

    if (uRenderMode == 2) {
      float normY = clamp(vLocalPos.y / max(0.4, uModelHeight), 0.0, 1.0);
      float fallbackFreedom = uHasSkin == 1
        ? clamp(1.0 - normY * 0.95, 0.0, 1.0)
        : clamp(abs(vLocalPos.x) / max(1.0, uModelHeight), 0.0, 1.0);
      float freedom = (uHasVertexColor == 1) ? clamp(vColor.r, 0.0, 1.0) : fallbackFreedom;
      vec3 heat = clothHeatmap(freedom);
      float diff = max(dot(N, normalize(vec3(0.5, 0.85, 0.4))), 0.0) * 0.65 + 0.35;
      fragColor = vec4(heat * diff + vec3(0.08) * pow(1.0 - ndotv, 2.5), 1.0);
      return;
    }

    vec3 keyDir;
    vec3 keyColor;
    vec3 fillDir = normalize(vec3(-0.65, 0.38, -0.65));
    vec3 fillColor;
    vec3 skyAmbient;
    vec3 groundAmbient;
    vec3 rimColor;
    float rimPow;
    float rimStrength;

    if (uLightingMode == 0) {
      // Renacimiento Sfumato (soft golden chiaroscuro + warm hemisphere bounce)
      keyDir = normalize(vec3(0.58, 0.80, 0.62));
      keyColor = vec3(1.06, 0.94, 0.78);
      fillColor = vec3(0.24, 0.25, 0.22);
      skyAmbient = vec3(0.29, 0.26, 0.22);
      groundAmbient = vec3(0.16, 0.12, 0.08);
      rimColor = vec3(1.0, 0.86, 0.56);
      rimPow = 2.8;
      rimStrength = 0.38;
    } else {
      // Street-Ink AAA (Stadium floodlight + cool hemisphere bounce + crisp cyan rim)
      keyDir = normalize(vec3(-0.45, 0.88, 0.68));
      keyColor = vec3(1.02, 1.06, 1.14);
      fillColor = vec3(0.18, 0.26, 0.38);
      skyAmbient = vec3(0.22, 0.27, 0.36);
      groundAmbient = vec3(0.10, 0.13, 0.18);
      rimColor = vec3(0.18, 0.92, 1.0);
      rimPow = 2.4;
      rimStrength = 0.44;
    }

    float hemi = clamp(N.y * 0.5 + 0.5, 0.0, 1.0);
    vec3 ambientColor = mix(groundAmbient, skyAmbient, hemi);

    float nDotL = max(dot(N, keyDir), 0.0);
    float nDotFill = max(dot(N, fillDir), 0.0);
    vec3 H = normalize(keyDir + V);
    float rough = clamp(uRoughness, 0.06, 1.0);
    float specPower = mix(96.0, 12.0, rough);
    float specMask = mix(0.16, 0.75, uMetallic) * (1.0 - rough * 0.62);
    float spec = pow(max(dot(N, H), 0.0), specPower) * specMask;
    float rim = pow(1.0 - ndotv, rimPow);

    // Subtle stepped ink shadow accent in Street-Ink or SMEAR mode
    if (uLightingMode == 1 || uRenderMode == 3) {
      nDotL = mix(nDotL, floor(nDotL * 3.5 + 0.35) / 3.5, 0.38);
    }

    vec3 lit =
      albedo * (ambientColor + keyColor * nDotL + fillColor * nDotFill) +
      keyColor * spec +
      rimColor * rim * rimStrength +
      uEmissive;

    // Gentle shoulder tone mapping without washed-out clipping
    lit = (lit * 1.32) / (lit + vec3(0.68));
    lit = clamp(pow(max(lit, vec3(0.0)), vec3(0.94)), 0.0, 1.0);

    float alpha = uRenderMode == 1 ? 0.24 : (uBaseColor.a * texSample.a);
    fragColor = vec4(lit, alpha);
  }`;

  const LINE_VERT_SRC = `#version 300 es
  precision highp float;
  layout(location = 0) in vec3 aPosition;
  uniform mat4 uMVP;
  uniform float uPointSize;
  void main() {
    gl_Position = uMVP * vec4(aPosition, 1.0);
    gl_PointSize = uPointSize;
  }`;

  const LINE_FRAG_SRC = `#version 300 es
  precision highp float;
  uniform vec4 uColor;
  out vec4 fragColor;
  void main() {
    fragColor = uColor;
  }`;

  function compileShader(gl, type, src) {
    const sh = gl.createShader(type);
    gl.shaderSource(sh, src);
    gl.compileShader(sh);
    if (!gl.getShaderParameter(sh, gl.COMPILE_STATUS)) {
      const log = gl.getShaderInfoLog(sh);
      gl.deleteShader(sh);
      throw new Error('Shader compile error: ' + log);
    }
    return sh;
  }

  function createProgram(gl, vsSrc, fsSrc) {
    const vs = compileShader(gl, gl.VERTEX_SHADER, vsSrc);
    const fs = compileShader(gl, gl.FRAGMENT_SHADER, fsSrc);
    const prog = gl.createProgram();
    gl.attachShader(prog, vs);
    gl.attachShader(prog, fs);
    gl.linkProgram(prog);
    gl.deleteShader(vs);
    gl.deleteShader(fs);
    if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) {
      const log = gl.getProgramInfoLog(prog);
      gl.deleteProgram(prog);
      throw new Error('Program link error: ' + log);
    }
    return prog;
  }

  // --------------------------------------------------------------------------
  // Viewer Singleton State & GPU Cache
  // --------------------------------------------------------------------------
  const viewer = {
    gl: null,
    canvas: null,
    meshProg: null,
    lineProg: null,
    meshLocs: {},
    lineLocs: {},
    whiteTex: null,
    anisoExt: null,
    maxAniso: 1,
    gridVAO: null,
    gridVertexCount: 0,
    lineBuf: null,
    lineVAO: null,
    modelCache: new Map(), // url -> { status: 'loading'|'ready'|'error', data }
    activeUrl: null,
    ballUrl: '../Assets/Models3D/Props/SM_Ball_TruncatedIcosahedron_32Panels.glb',
    lastStats: {
      loaded: false,
      file: '',
      byteLength: 0,
      verts: 0,
      tris: 0,
      joints: 0,
      materials: 0,
      clips: 0,
      heightM: 0,
      curKf: 1,
      totalKf: 1,
      fps: 60.0
    },
    _lastFrameTime: 0
  };

  function createWhiteTexture(gl) {
    const tex = gl.createTexture();
    gl.bindTexture(gl.TEXTURE_2D, tex);
    // glTF 2.0 UV (0,0) = top-left of image memory -> UNPACK_FLIP_Y_WEBGL = false
    gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, false);
    gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, 1, 1, 0, gl.RGBA, gl.UNSIGNED_BYTE, new Uint8Array([255, 255, 255, 255]));
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.REPEAT);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.REPEAT);
    gl.bindTexture(gl.TEXTURE_2D, null);
    return tex;
  }

  function buildGridBuffer(gl) {
    const verts = [];
    const extent = 2.0;
    const step = 0.4;
    for (let i = -5; i <= 5; i++) {
      const g = i * step;
      verts.push(g, 0, -extent, g, 0, extent);
      verts.push(-extent, 0, g, extent, 0, g);
    }
    const vao = gl.createVertexArray();
    gl.bindVertexArray(vao);
    const vbo = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, vbo);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(verts), gl.STATIC_DRAW);
    gl.enableVertexAttribArray(0);
    gl.vertexAttribPointer(0, 3, gl.FLOAT, false, 0, 0);
    gl.bindVertexArray(null);
    viewer.gridVAO = vao;
    viewer.gridVertexCount = verts.length / 3;
  }

  function buildDynamicLineVAO(gl) {
    const vao = gl.createVertexArray();
    gl.bindVertexArray(vao);
    const vbo = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, vbo);
    gl.enableVertexAttribArray(0);
    gl.vertexAttribPointer(0, 3, gl.FLOAT, false, 0, 0);
    gl.bindVertexArray(null);
    viewer.lineVAO = vao;
    viewer.lineBuf = vbo;
  }

  function uploadGLBToGPU(gl, parsed, byteLength = 0) {
    const { gltf, binBuffer } = parsed;

    // Parse glTF 2.0 samplers, embedded images (bufferView/uri), and textures
    const samplers = (gltf.samplers || []).map((s) => ({
      magFilter: s.magFilter || gl.LINEAR,
      minFilter: s.minFilter || gl.LINEAR_MIPMAP_LINEAR,
      wrapS: s.wrapS || gl.REPEAT,
      wrapT: s.wrapT || gl.REPEAT
    }));

    const images = (gltf.images || []).map((imgDef) => {
      const imgEntry = { img: null, ready: false, blobUrl: null };
      if (imgDef.bufferView !== undefined && gltf.bufferViews && gltf.bufferViews[imgDef.bufferView]) {
        const bv = gltf.bufferViews[imgDef.bufferView];
        const bOff = bv.byteOffset || 0;
        const bLen = bv.byteLength || 0;
        const imgBytes = binBuffer.subarray(bOff, bOff + bLen);
        const blob = new Blob([imgBytes], { type: imgDef.mimeType || 'image/png' });
        imgEntry.blobUrl = URL.createObjectURL(blob);
        const img = new Image();
        img.onload = () => {
          imgEntry.ready = true;
          if (imgEntry.blobUrl) {
            URL.revokeObjectURL(imgEntry.blobUrl);
            imgEntry.blobUrl = null;
          }
        };
        img.onerror = () => {
          if (imgEntry.blobUrl) {
            URL.revokeObjectURL(imgEntry.blobUrl);
            imgEntry.blobUrl = null;
          }
        };
        img.src = imgEntry.blobUrl;
        imgEntry.img = img;
      } else if (imgDef.uri) {
        const img = new Image();
        img.onload = () => { imgEntry.ready = true; };
        img.src = imgDef.uri;
        imgEntry.img = img;
      }
      return imgEntry;
    });

    const textures = (gltf.textures || []).map((texDef) => {
      const glTex = gl.createTexture();
      const smp = texDef.sampler !== undefined && samplers[texDef.sampler]
        ? samplers[texDef.sampler]
        : { magFilter: gl.LINEAR, minFilter: gl.LINEAR_MIPMAP_LINEAR, wrapS: gl.REPEAT, wrapT: gl.REPEAT };
      const imgEntry = texDef.source !== undefined ? images[texDef.source] : null;

      // Seed with 1x1 white placeholder so texture unit stays renderable while async decode completes
      gl.bindTexture(gl.TEXTURE_2D, glTex);
      gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, false);
      gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, 1, 1, 0, gl.RGBA, gl.UNSIGNED_BYTE, new Uint8Array([255, 255, 255, 255]));
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, smp.wrapS);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, smp.wrapT);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, smp.magFilter);
      gl.bindTexture(gl.TEXTURE_2D, null);

      return { glTex, sampler: smp, imgEntry, uploaded: false };
    });

    const materials = (gltf.materials || []).map((m) => {
      const pbr = m.pbrMetallicRoughness || {};
      const bct = pbr.baseColorTexture;
      return {
        name: m.name || 'Mat',
        baseColorFactor: pbr.baseColorFactor ? Float32Array.from(pbr.baseColorFactor) : new Float32Array([1.0, 1.0, 1.0, 1.0]),
        baseColorTexIndex: bct && bct.index !== undefined ? bct.index : -1,
        metallicFactor: pbr.metallicFactor !== undefined ? pbr.metallicFactor : 0.1,
        roughnessFactor: pbr.roughnessFactor !== undefined ? pbr.roughnessFactor : 0.6,
        emissiveFactor: m.emissiveFactor ? Float32Array.from(m.emissiveFactor) : new Float32Array([0, 0, 0])
      };
    });

    const nodes = (gltf.nodes || []).map((n) => ({
      name: n.name || '',
      mesh: n.mesh,
      skin: n.skin,
      children: n.children ? n.children.slice() : [],
      translation: n.translation ? Float32Array.from(n.translation) : new Float32Array([0, 0, 0]),
      rotation: n.rotation ? Float32Array.from(n.rotation) : new Float32Array([0, 0, 0, 1]),
      scale: n.scale ? Float32Array.from(n.scale) : new Float32Array([1, 1, 1]),
      matrix: n.matrix ? Float32Array.from(n.matrix) : null
    }));

    // Build parent lookup to find root nodes
    const hasParent = new Uint8Array(nodes.length);
    const parentOf = new Int32Array(nodes.length).fill(-1);
    nodes.forEach((n, idx) => {
      n.children.forEach((ch) => {
        hasParent[ch] = 1;
        parentOf[ch] = idx;
      });
    });
    const rootNodes = [];
    for (let i = 0; i < nodes.length; i++) {
      if (!hasParent[i]) rootNodes.push(i);
    }

    let skins = [];
    if (gltf.skins && gltf.skins.length > 0) {
      skins = gltf.skins.map((s) => {
        const ibmFlat = s.inverseBindMatrices !== undefined
          ? readAccessor(gltf, binBuffer, s.inverseBindMatrices)
          : null;
        const ibms = [];
        for (let i = 0; i < s.joints.length; i++) {
          const m = new Float32Array(16);
          if (ibmFlat) m.set(ibmFlat.subarray(i * 16, i * 16 + 16));
          else mat4Identity(m);
          ibms.push(m);
        }
        return {
          joints: s.joints.slice(),
          ibms
        };
      });
    }

    const animations = new Map();
    (gltf.animations || []).forEach((anim) => {
      const samplers = (anim.samplers || []).map((smp) => {
        const input = Float32Array.from(readAccessor(gltf, binBuffer, smp.input));
        const output = Float32Array.from(readAccessor(gltf, binBuffer, smp.output));
        return {
          input,
          output,
          interpolation: smp.interpolation || 'LINEAR'
        };
      });
      const channels = (anim.channels || []).map((ch) => ({
        sampler: ch.sampler,
        node: ch.target.node,
        path: ch.target.path
      }));
      const maxTime = samplers.reduce((mx, s) => (s.input.length ? Math.max(mx, s.input[s.input.length - 1]) : mx), 0);
      animations.set(anim.name || 'Clip', { name: anim.name, samplers, channels, duration: maxTime });
    });

    // Compute bounds & upload mesh primitives
    const minB = [Infinity, Infinity, Infinity];
    const maxB = [-Infinity, -Infinity, -Infinity];
    let totalVerts = 0;
    let totalTris = 0;

    const meshes = (gltf.meshes || []).map((mesh) => {
      const primitives = (mesh.primitives || []).map((prim, pIdx) => {
        const attrs = prim.attributes || {};
        const pos = readAccessor(gltf, binBuffer, attrs.POSITION);
        const vertCount = pos.length / 3;
        totalVerts += vertCount;

        for (let i = 0; i < pos.length; i += 3) {
          if (pos[i] < minB[0]) minB[0] = pos[i];
          if (pos[i + 1] < minB[1]) minB[1] = pos[i + 1];
          if (pos[i + 2] < minB[2]) minB[2] = pos[i + 2];
          if (pos[i] > maxB[0]) maxB[0] = pos[i];
          if (pos[i + 1] > maxB[1]) maxB[1] = pos[i + 1];
          if (pos[i + 2] > maxB[2]) maxB[2] = pos[i + 2];
        }

        const norm = attrs.NORMAL !== undefined
          ? new Float32Array(readAccessor(gltf, binBuffer, attrs.NORMAL))
          : new Float32Array(vertCount * 3);

        let hasVertexColor = 0;
        let color = new Float32Array(vertCount * 4);
        if (attrs.COLOR_0 !== undefined) {
          hasVertexColor = 1;
          const rawCol = readAccessor(gltf, binBuffer, attrs.COLOR_0);
          const colAcc = gltf.accessors[attrs.COLOR_0];
          const comp = GLTF_TYPE_COMPONENTS[colAcc.type] || 4;
          const scale = colAcc.componentType === 5121 ? (1 / 255) : (colAcc.componentType === 5123 ? (1 / 65535) : 1);
          for (let i = 0; i < vertCount; i++) {
            color[i * 4] = rawCol[i * comp] * scale;
            color[i * 4 + 1] = rawCol[i * comp + 1] * scale;
            color[i * 4 + 2] = rawCol[i * comp + 2] * scale;
            color[i * 4 + 3] = comp === 4 ? rawCol[i * comp + 3] * scale : 1.0;
          }
        } else {
          for (let i = 0; i < vertCount; i++) {
            color[i * 4] = 1; color[i * 4 + 1] = 1; color[i * 4 + 2] = 1; color[i * 4 + 3] = 1;
          }
        }

        const joints = new Float32Array(vertCount * 4);
        if (attrs.JOINTS_0 !== undefined) {
          const rawJ = readAccessor(gltf, binBuffer, attrs.JOINTS_0);
          for (let i = 0; i < rawJ.length; i++) joints[i] = rawJ[i];
        }

        const weights = new Float32Array(vertCount * 4);
        if (attrs.WEIGHTS_0 !== undefined) {
          const rawW = readAccessor(gltf, binBuffer, attrs.WEIGHTS_0);
          const wAcc = gltf.accessors[attrs.WEIGHTS_0];
          const scale = wAcc.componentType === 5121 ? (1 / 255) : (wAcc.componentType === 5123 ? (1 / 65535) : 1);
          for (let i = 0; i < rawW.length; i++) weights[i] = rawW[i] * scale;
        }

        let hasUv = 0;
        const uv = new Float32Array(vertCount * 2);
        if (attrs.TEXCOORD_0 !== undefined) {
          hasUv = 1;
          const rawUv = readAccessor(gltf, binBuffer, attrs.TEXCOORD_0);
          const uvAcc = gltf.accessors[attrs.TEXCOORD_0];
          const comp = GLTF_TYPE_COMPONENTS[uvAcc.type] || 2;
          const scale = uvAcc.componentType === 5121 ? (1 / 255) : (uvAcc.componentType === 5123 ? (1 / 65535) : 1);
          for (let i = 0; i < vertCount; i++) {
            uv[i * 2] = rawUv[i * comp] * scale;
            uv[i * 2 + 1] = rawUv[i * comp + 1] * scale;
          }
        }

        let indices;
        let indexType = gl.UNSIGNED_SHORT;
        if (prim.indices !== undefined) {
          const rawIdx = readAccessor(gltf, binBuffer, prim.indices);
          if (rawIdx instanceof Uint32Array) {
            indices = rawIdx;
            indexType = gl.UNSIGNED_INT;
          } else {
            indices = new Uint16Array(rawIdx);
            indexType = gl.UNSIGNED_SHORT;
          }
        } else {
          indices = new Uint16Array(vertCount);
          for (let i = 0; i < vertCount; i++) indices[i] = i;
        }
        totalTris += Math.floor(indices.length / 3);

        // Build wireframe edge index buffer
        const wireIndices = new (indexType === gl.UNSIGNED_INT ? Uint32Array : Uint16Array)(Math.floor(indices.length / 3) * 6);
        let wi = 0;
        for (let t = 0; t + 2 < indices.length; t += 3) {
          const a = indices[t], b = indices[t + 1], c = indices[t + 2];
          wireIndices[wi++] = a; wireIndices[wi++] = b;
          wireIndices[wi++] = b; wireIndices[wi++] = c;
          wireIndices[wi++] = c; wireIndices[wi++] = a;
        }

        const vao = gl.createVertexArray();
        gl.bindVertexArray(vao);

        const bindAttr = (loc, data, size) => {
          const buf = gl.createBuffer();
          gl.bindBuffer(gl.ARRAY_BUFFER, buf);
          gl.bufferData(gl.ARRAY_BUFFER, data, gl.STATIC_DRAW);
          gl.enableVertexAttribArray(loc);
          gl.vertexAttribPointer(loc, size, gl.FLOAT, false, 0, 0);
        };

        bindAttr(0, new Float32Array(pos), 3);
        bindAttr(1, norm, 3);
        bindAttr(2, color, 4);
        bindAttr(3, joints, 4);
        bindAttr(4, weights, 4);
        bindAttr(5, uv, 2);

        const ibo = gl.createBuffer();
        gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, ibo);
        gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, indices, gl.STATIC_DRAW);
        gl.bindVertexArray(null);

        // Wireframe VAO reusing position buffer
        const wireVao = gl.createVertexArray();
        gl.bindVertexArray(wireVao);
        const wirePosBuf = gl.createBuffer();
        gl.bindBuffer(gl.ARRAY_BUFFER, wirePosBuf);
        gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(pos), gl.STATIC_DRAW);
        gl.enableVertexAttribArray(0);
        gl.vertexAttribPointer(0, 3, gl.FLOAT, false, 0, 0);
        const wireIbo = gl.createBuffer();
        gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, wireIbo);
        gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, wireIndices, gl.STATIC_DRAW);
        gl.bindVertexArray(null);

        return {
          vao,
          wireVao,
          ibo,
          indexCount: indices.length,
          wireCount: wireIndices.length,
          indexType,
          materialIndex: prim.material !== undefined ? prim.material : 0,
          hasVertexColor,
          hasUv,
          primIndex: pIdx
        };
      });
      return { primitives };
    });

    if (!Number.isFinite(minB[0])) {
      minB[0] = -0.5; minB[1] = 0; minB[2] = -0.5;
      maxB[0] = 0.5; maxB[1] = 1.8; maxB[2] = 0.5;
    }

    const sizeX = maxB[0] - minB[0];
    const sizeY = maxB[1] - minB[1];
    const sizeZ = maxB[2] - minB[2];
    const maxSpan = Math.max(sizeX, sizeY, sizeZ, 0.25);

    return {
      nodes,
      rootNodes,
      parentOf,
      skins,
      animations,
      materials,
      textures,
      meshes,
      byteLength,
      bounds: {
        min: minB,
        max: maxB,
        center: [
          (minB[0] + maxB[0]) * 0.5,
          (minB[1] + maxB[1]) * 0.5,
          (minB[2] + maxB[2]) * 0.5
        ],
        size: [sizeX, sizeY, sizeZ],
        maxSpan
      },
      totalVerts,
      totalTris
    };
  }

  function requestModel(url, ctx = viewer) {
    if (!url || !ctx.gl) return null;
    const cached = ctx.modelCache.get(url);
    if (cached) return cached;

    const entry = { status: 'loading', data: null };
    ctx.modelCache.set(url, entry);

    fetch(url)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.arrayBuffer();
      })
      .then((buf) => {
        const parsed = parseGLB(buf);
        entry.data = uploadGLBToGPU(ctx.gl, parsed, buf.byteLength);
        entry.status = 'ready';
      })
      .catch((err) => {
        console.warn('[SAFWglViewer] Failed to load GLB:', url, err);
        entry.status = 'error';
      });

    return entry;
  }

  // --------------------------------------------------------------------------
  // Animation & Skeleton Pose Evaluation
  // --------------------------------------------------------------------------
  function evaluateAnimation(model, clipName, animClockFrames, loop = true) {
    const nodeCount = model.nodes.length;
    const localT = model.nodes.map((n) => Float32Array.from(n.translation));
    const localR = model.nodes.map((n) => Float32Array.from(n.rotation));
    const localS = model.nodes.map((n) => Float32Array.from(n.scale));

    const clip = model.animations.get(clipName) || model.animations.values().next().value || null;
    let curKf = 1;
    let totalKf = 1;

    if (clip && clip.duration > 0) {
      const timeSecRaw = Math.max(0, animClockFrames) / 60.0;
      const t = loop ? (timeSecRaw % clip.duration) : Math.min(timeSecRaw, Math.max(0, clip.duration - 0.0001));
      const firstSmp = clip.samplers[0];
      if (firstSmp && firstSmp.input.length > 0) {
        totalKf = firstSmp.input.length;
        curKf = loop
          ? ((Math.floor(animClockFrames) % totalKf) + 1)
          : Math.min(totalKf, Math.max(1, Math.floor(animClockFrames) + 1));
      }

      for (let c = 0; c < clip.channels.length; c++) {
        const ch = clip.channels[c];
        const smp = clip.samplers[ch.sampler];
        if (!smp || smp.input.length === 0) continue;
        const times = smp.input;
        const vals = smp.output;
        const nIdx = ch.node;

        let idx0 = 0;
        let idx1 = 0;
        let alpha = 0;

        if (t <= times[0] || times.length === 1) {
          idx0 = 0; idx1 = 0; alpha = 0;
        } else if (t >= times[times.length - 1]) {
          idx0 = times.length - 1; idx1 = idx0; alpha = 0;
        } else {
          // Binary search for keyframe segment
          let lo = 0, hi = times.length - 1;
          while (lo + 1 < hi) {
            const mid = (lo + hi) >> 1;
            if (times[mid] <= t) lo = mid;
            else hi = mid;
          }
          idx0 = lo;
          idx1 = hi;
          const dt = times[idx1] - times[idx0];
          alpha = (dt > 1e-6 && smp.interpolation !== 'STEP') ? (t - times[idx0]) / dt : 0;
        }

        if (ch.path === 'translation') {
          const o0 = idx0 * 3, o1 = idx1 * 3;
          localT[nIdx][0] = vals[o0] + (vals[o1] - vals[o0]) * alpha;
          localT[nIdx][1] = vals[o0 + 1] + (vals[o1 + 1] - vals[o0 + 1]) * alpha;
          localT[nIdx][2] = vals[o0 + 2] + (vals[o1 + 2] - vals[o0 + 2]) * alpha;
        } else if (ch.path === 'scale') {
          const o0 = idx0 * 3, o1 = idx1 * 3;
          localS[nIdx][0] = vals[o0] + (vals[o1] - vals[o0]) * alpha;
          localS[nIdx][1] = vals[o0 + 1] + (vals[o1 + 1] - vals[o0 + 1]) * alpha;
          localS[nIdx][2] = vals[o0 + 2] + (vals[o1 + 2] - vals[o0 + 2]) * alpha;
        } else if (ch.path === 'rotation') {
          const o0 = idx0 * 4, o1 = idx1 * 4;
          const qa = [vals[o0], vals[o0 + 1], vals[o0 + 2], vals[o0 + 3]];
          if (alpha <= 0.0001 || idx0 === idx1) {
            localR[nIdx].set(qa);
          } else {
            const qb = [vals[o1], vals[o1 + 1], vals[o1 + 2], vals[o1 + 3]];
            quatSlerp(localR[nIdx], qa, qb, alpha);
          }
        }
      }
    }

    const worldMats = new Array(nodeCount);
    const localMat = new Float32Array(16);

    function traverse(nodeIdx, parentWorld) {
      const node = model.nodes[nodeIdx];
      if (node.matrix) {
        localMat.set(node.matrix);
      } else {
        mat4FromTRS(localMat, localT[nodeIdx], localR[nodeIdx], localS[nodeIdx]);
      }
      const wm = new Float32Array(16);
      if (parentWorld) mat4Multiply(wm, parentWorld, localMat);
      else wm.set(localMat);
      worldMats[nodeIdx] = wm;

      for (let i = 0; i < node.children.length; i++) {
        traverse(node.children[i], wm);
      }
    }

    for (let r = 0; r < model.rootNodes.length; r++) {
      traverse(model.rootNodes[r], null);
    }

    return { worldMats, curKf, totalKf };
  }

  // --------------------------------------------------------------------------
  // Drawing Helpers
  // --------------------------------------------------------------------------
  function drawLines(mvp, vertsArray, color, mode, pointSize = 5.0, ctx = viewer) {
    const gl = ctx.gl;
    if (!vertsArray || vertsArray.length === 0) return;
    gl.useProgram(ctx.lineProg);
    gl.uniformMatrix4fv(ctx.lineLocs.uMVP, false, mvp);
    gl.uniform4fv(ctx.lineLocs.uColor, color);
    gl.uniform1f(ctx.lineLocs.uPointSize, pointSize);

    gl.bindVertexArray(ctx.lineVAO);
    gl.bindBuffer(gl.ARRAY_BUFFER, ctx.lineBuf);
    gl.bufferData(gl.ARRAY_BUFFER, vertsArray instanceof Float32Array ? vertsArray : new Float32Array(vertsArray), gl.DYNAMIC_DRAW);
    gl.drawArrays(mode, 0, vertsArray.length / 3);
    gl.bindVertexArray(null);
  }

  function drawModel(model, modelMatrix, viewProj, view, proj, cameraPos, state, poseEval, ctx = viewer, extraEmissive = null) {
    const gl = ctx.gl;
    const renderModeMap = { SHADED: 0, SKELETON: 1, CLOTH: 2, SMEAR: 3 };
    const rMode = renderModeMap[state.mode] ?? 0;
    const lMode = state.lighting === 'SFUMATO' ? 0 : 1;

    gl.useProgram(ctx.meshProg);
    gl.uniformMatrix4fv(ctx.meshLocs.uView, false, view);
    gl.uniformMatrix4fv(ctx.meshLocs.uProj, false, proj);
    gl.uniform3fv(ctx.meshLocs.uCameraPos, cameraPos);
    gl.uniform1i(ctx.meshLocs.uLightingMode, lMode);
    gl.uniform1i(ctx.meshLocs.uRenderMode, rMode);
    gl.uniform1f(ctx.meshLocs.uWindPct, (state.windPct || 0) / 100);
    gl.uniform1f(ctx.meshLocs.uTime, (state.tick || 0) / 60.0);
    gl.uniform1f(ctx.meshLocs.uSmearScale, state.smearScale || 1.0);
    gl.uniform1f(ctx.meshLocs.uModelHeight, model.bounds.size[1] || 1.8);

    // Prepare joint matrix buffer if skinned
    const jointBuffer = new Float32Array(64 * 16);
    for (let j = 0; j < 64; j++) mat4Identity(jointBuffer.subarray(j * 16, j * 16 + 16));

    // Render every node that has a mesh
    for (let nIdx = 0; nIdx < model.nodes.length; nIdx++) {
      const node = model.nodes[nIdx];
      if (node.mesh === undefined) continue;
      const mesh = model.meshes[node.mesh];
      if (!mesh) continue;

      const nodeWorld = poseEval.worldMats[nIdx] || mat4Identity();
      const fullModel = new Float32Array(16);

      const hasSkin = node.skin !== undefined && model.skins[node.skin] ? 1 : 0;
      if (hasSkin) {
        // Skinned vertices are already placed in world space by joint matrices; only apply scene modelMatrix
        fullModel.set(modelMatrix);
        const skin = model.skins[node.skin];
        const count = Math.min(64, skin.joints.length);
        for (let j = 0; j < count; j++) {
          const jNode = skin.joints[j];
          const jWorld = poseEval.worldMats[jNode] || mat4Identity();
          mat4Multiply(jointBuffer.subarray(j * 16, j * 16 + 16), jWorld, skin.ibms[j]);
        }
        gl.uniformMatrix4fv(ctx.meshLocs.uJointMatrices, false, jointBuffer);
      } else {
        mat4Multiply(fullModel, modelMatrix, nodeWorld);
      }

      gl.uniform1i(ctx.meshLocs.uHasSkin, hasSkin);
      gl.uniformMatrix4fv(ctx.meshLocs.uModel, false, fullModel);

      if (rMode === 1) {
        gl.enable(gl.BLEND);
        gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);
        gl.depthMask(false);
      }

      for (let p = 0; p < mesh.primitives.length; p++) {
        const prim = mesh.primitives[p];
        const mat = model.materials[prim.materialIndex] || {
          baseColorFactor: new Float32Array([1.0, 1.0, 1.0, 1.0]),
          baseColorTexIndex: -1,
          emissiveFactor: new Float32Array([0, 0, 0]),
          metallicFactor: 0.1,
          roughnessFactor: 0.6
        };

        const texEntry = (mat.baseColorTexIndex >= 0 && model.textures && model.textures[mat.baseColorTexIndex])
          ? model.textures[mat.baseColorTexIndex]
          : null;

        gl.activeTexture(gl.TEXTURE0);
        if (texEntry && texEntry.glTex) {
          gl.bindTexture(gl.TEXTURE_2D, texEntry.glTex);
          if (!texEntry.uploaded && texEntry.imgEntry && texEntry.imgEntry.ready && texEntry.imgEntry.img) {
            // glTF 2.0 spec: UV (0,0) is TOP-LEFT of PNG/JPEG image memory,
            // so UNPACK_FLIP_Y_WEBGL MUST be false to match Blender/glTF TEXCOORD_0.
            gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, false);
            gl.pixelStorei(gl.UNPACK_PREMULTIPLY_ALPHA_WEBGL, false);
            gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, texEntry.imgEntry.img);
            gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, texEntry.sampler.wrapS);
            gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, texEntry.sampler.wrapT);
            gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, texEntry.sampler.magFilter);
            gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, texEntry.sampler.minFilter);
            gl.generateMipmap(gl.TEXTURE_2D);
            if (ctx.anisoExt) {
              gl.texParameterf(gl.TEXTURE_2D, ctx.anisoExt.TEXTURE_MAX_ANISOTROPY_EXT, Math.min(8, ctx.maxAniso || 4));
            }
            texEntry.uploaded = true;
          }
        } else {
          gl.bindTexture(gl.TEXTURE_2D, ctx.whiteTex);
        }

        const hasBaseColorTex = (texEntry && texEntry.uploaded && prim.hasUv) ? 1 : 0;
        const em = extraEmissive
          ? [mat.emissiveFactor[0] + extraEmissive[0], mat.emissiveFactor[1] + extraEmissive[1], mat.emissiveFactor[2] + extraEmissive[2]]
          : mat.emissiveFactor;
        gl.uniform1i(ctx.meshLocs.uBaseColorTex, 0);
        gl.uniform1i(ctx.meshLocs.uHasBaseColorTex, hasBaseColorTex);
        gl.uniform4fv(ctx.meshLocs.uBaseColor, mat.baseColorFactor);
        gl.uniform3fv(ctx.meshLocs.uEmissive, em);
        gl.uniform1f(ctx.meshLocs.uMetallic, mat.metallicFactor);
        gl.uniform1f(ctx.meshLocs.uRoughness, mat.roughnessFactor);
        gl.uniform1i(ctx.meshLocs.uHasVertexColor, prim.hasVertexColor);
        gl.uniform1i(ctx.meshLocs.uPrimIndex, prim.primIndex);

        gl.bindVertexArray(prim.vao);
        gl.drawElements(gl.TRIANGLES, prim.indexCount, prim.indexType, 0);
        gl.bindVertexArray(null);
      }

      if (rMode === 1) {
        gl.depthMask(true);
        gl.disable(gl.BLEND);

        // Draw structural wireframe over ghosted mesh in SKELETON mode
        const mvp = new Float32Array(16);
        mat4Multiply(mvp, viewProj, fullModel);
        gl.useProgram(ctx.lineProg);
        gl.uniformMatrix4fv(ctx.lineLocs.uMVP, false, mvp);
        gl.uniform4fv(ctx.lineLocs.uColor, hasSkin ? [0.0, 0.90, 1.0, 0.32] : [0.96, 0.77, 0.32, 0.55]);
        for (let p = 0; p < mesh.primitives.length; p++) {
          const prim = mesh.primitives[p];
          if (!hasSkin) {
            gl.bindVertexArray(prim.wireVao);
            gl.drawElements(gl.LINES, prim.wireCount, prim.indexType, 0);
            gl.bindVertexArray(null);
          }
        }
      }
    }

    // Draw real glTF 3D Skeleton bones & joints when in SKELETON or SMEAR mode
    if ((rMode === 1 || rMode === 3) && model.skins.length > 0) {
      const skin = model.skins[0];
      const jointSet = new Set(skin.joints);
      const boneLines = [];
      const jointPts = [];

      for (let i = 0; i < skin.joints.length; i++) {
        const jNode = skin.joints[i];
        const jm = poseEval.worldMats[jNode];
        if (!jm) continue;
        jointPts.push(jm[12], jm[13], jm[14]);
        const pIdx = model.parentOf[jNode];
        if (pIdx >= 0 && (jointSet.has(pIdx) || model.nodes[pIdx].name === 'root')) {
          const pm = poseEval.worldMats[pIdx];
          if (pm) {
            boneLines.push(pm[12], pm[13], pm[14], jm[12], jm[13], jm[14]);
          }
        }
      }

      const mvp = new Float32Array(16);
      mat4Multiply(mvp, viewProj, modelMatrix);
      gl.disable(gl.DEPTH_TEST);
      drawLines(mvp, boneLines, [0.96, 0.77, 0.32, 1.0], gl.LINES, 5.0, ctx);
      drawLines(mvp, jointPts, [0.0, 0.90, 1.0, 1.0], gl.POINTS, 6.0, ctx);
      gl.enable(gl.DEPTH_TEST);
    }

    // Draw AABB Hurtbox cage in SMEAR mode or Anim_214SK_Scorpion
    if (rMode === 3 || state.pose === 'Anim_214SK_Scorpion') {
      const bMin = model.bounds.min;
      const bMax = model.bounds.max;
      const topY = state.pose === 'Anim_214SK_Scorpion' ? bMax[1] * 0.65 : bMax[1];
      const x0 = Math.min(-0.32, bMin[0] * 0.55), x1 = Math.max(0.32, bMax[0] * 0.55);
      const y0 = Math.max(0, bMin[1]), y1 = topY;
      const z0 = -0.25, z1 = 0.25;
      const boxVerts = [
        x0,y0,z0, x1,y0,z0,  x1,y0,z0, x1,y1,z0,  x1,y1,z0, x0,y1,z0,  x0,y1,z0, x0,y0,z0,
        x0,y0,z1, x1,y0,z1,  x1,y0,z1, x1,y1,z1,  x1,y1,z1, x0,y1,z1,  x0,y1,z1, x0,y0,z1,
        x0,y0,z0, x0,y0,z1,  x1,y0,z0, x1,y0,z1,  x1,y1,z0, x1,y1,z1,  x0,y1,z0, x0,y1,z1
      ];
      const boxColor = state.pose === 'Anim_214SK_Scorpion' ? [0.0, 0.90, 1.0, 1.0] : [0.0, 0.90, 0.46, 1.0];
      const mvp = new Float32Array(16);
      mat4Multiply(mvp, viewProj, modelMatrix);
      drawLines(mvp, boxVerts, boxColor, gl.LINES);
    }
  }

  // --------------------------------------------------------------------------
  // Public API: SAFWglViewer
  // --------------------------------------------------------------------------
  const SAFWglViewer = {
    init(canvas) {
      if (!canvas) return false;
      try {
        // Probe WebGL2 + GLSL compilation on a disposable offscreen canvas first so
        // an unsupported environment never locks `canvas` away from getContext('2d').
        const probe = document.createElement('canvas');
        const probeGl = probe.getContext('webgl2');
        if (!probeGl || !(probeGl instanceof WebGL2RenderingContext)) {
          return false;
        }
        const testMeshProg = createProgram(probeGl, MESH_VERT_SRC, MESH_FRAG_SRC);
        const testLineProg = createProgram(probeGl, LINE_VERT_SRC, LINE_FRAG_SRC);
        probeGl.deleteProgram(testMeshProg);
        probeGl.deleteProgram(testLineProg);
        const loseExt = probeGl.getExtension('WEBGL_lose_context');
        if (loseExt) loseExt.loseContext();

        const gl = canvas.getContext('webgl2', { antialias: true, alpha: false, preserveDrawingBuffer: true });
        if (!gl || !(gl instanceof WebGL2RenderingContext) || gl.isContextLost()) {
          return false;
        }
        viewer.canvas = canvas;
        viewer.gl = gl;

        viewer.meshProg = createProgram(gl, MESH_VERT_SRC, MESH_FRAG_SRC);
        viewer.lineProg = createProgram(gl, LINE_VERT_SRC, LINE_FRAG_SRC);

        [
          'uModel', 'uView', 'uProj', 'uHasSkin', 'uJointMatrices', 'uRenderMode',
          'uWindPct', 'uTime', 'uSmearScale', 'uPrimIndex', 'uCameraPos',
          'uBaseColor', 'uEmissive', 'uMetallic', 'uRoughness',
          'uHasVertexColor', 'uBaseColorTex', 'uHasBaseColorTex',
          'uLightingMode', 'uModelHeight'
        ].forEach((name) => {
          viewer.meshLocs[name] = gl.getUniformLocation(viewer.meshProg, name);
        });

        ['uMVP', 'uColor', 'uPointSize'].forEach((name) => {
          viewer.lineLocs[name] = gl.getUniformLocation(viewer.lineProg, name);
        });

        viewer.whiteTex = createWhiteTexture(gl);
        viewer.anisoExt = gl.getExtension('EXT_texture_filter_anisotropic');
        viewer.maxAniso = viewer.anisoExt ? gl.getParameter(viewer.anisoExt.MAX_TEXTURE_MAX_ANISOTROPY_EXT) : 1;

        buildGridBuffer(gl);
        buildDynamicLineVAO(gl);
        viewer._lastFrameTime = performance.now();
        return true;
      } catch (err) {
        console.warn('[SAFWglViewer] WebGL2 initialization fallback:', err);
        viewer.gl = null;
        return false;
      }
    },

    isReady() {
      return Boolean(viewer.gl && viewer.gl instanceof WebGL2RenderingContext && !viewer.gl.isContextLost());
    },

    getStats() {
      return viewer.lastStats;
    },

    render(url, state) {
      const gl = viewer.gl;
      if (!gl) return false;

      const now = performance.now();
      const dtMs = now - viewer._lastFrameTime;
      viewer._lastFrameTime = now;
      if (dtMs > 0 && dtMs < 200) {
        viewer.lastStats.fps = Math.min(60.0, 1000 / Math.max(16.66, dtMs));
      }

      const w = viewer.canvas.width;
      const h = viewer.canvas.height;
      gl.viewport(0, 0, w, h);
      gl.enable(gl.DEPTH_TEST);
      gl.disable(gl.CULL_FACE);

      const isSfumato = state.lighting === 'SFUMATO';
      if (isSfumato) {
        gl.clearColor(0.11, 0.075, 0.04, 1.0); // Warm Sfumato chiaroscuro umber
      } else {
        gl.clearColor(0.035, 0.055, 0.10, 1.0); // Deep Street-Ink stadium night
      }
      gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);

      const entry = requestModel(url);
      const ballEntry = state.category === 'FIGHTERS' ? requestModel(viewer.ballUrl) : null;

      // Camera computation scaled to the active model bounds
      let target = [0, 0.9, 0];
      let baseDist = 3.2;
      let modelScale = 1.0;

      if (entry && entry.status === 'ready' && entry.data) {
        const b = entry.data.bounds;
        if (state.category === 'STAGES' || state.propKey === 'ARENA_WALLS') {
          modelScale = 2.6 / Math.max(1.0, b.maxSpan);
          target = [b.center[0] * modelScale, b.center[1] * modelScale * 0.5, b.center[2] * modelScale];
          baseDist = 3.1;
        } else if (state.category === 'PROPS' && state.propKey === 'BALL_32') {
          modelScale = 1.6 / Math.max(0.1, b.maxSpan);
          target = [b.center[0] * modelScale, b.center[1] * modelScale, b.center[2] * modelScale];
          baseDist = 2.8;
        } else {
          // Fighter (~1.7m - 2.15m)
          modelScale = 1.0;
          target = [0, b.size[1] * 0.52, 0];
          baseDist = 2.95;
        }
      }

      const camDist = baseDist / Math.max(0.4, state.zoom || 1.0);
      const yaw = state.yaw || 0.55;
      const pitch = state.pitch || 0.18;
      const eye = [
        target[0] + Math.sin(yaw) * Math.cos(pitch) * camDist,
        target[1] + Math.sin(pitch) * camDist + 0.18,
        target[2] + Math.cos(yaw) * Math.cos(pitch) * camDist
      ];

      const proj = new Float32Array(16);
      const view = new Float32Array(16);
      const viewProj = new Float32Array(16);
      mat4Perspective(proj, (44 * Math.PI) / 180, w / Math.max(1, h), 0.05, 120.0);
      mat4LookAt(view, eye, target, [0, 1, 0]);
      mat4Multiply(viewProj, proj, view);

      // Draw Floor Grid
      gl.useProgram(viewer.lineProg);
      gl.uniformMatrix4fv(viewer.lineLocs.uMVP, false, viewProj);
      gl.uniform4fv(viewer.lineLocs.uColor, isSfumato ? [0.83, 0.64, 0.28, 0.35] : [0.0, 0.90, 1.0, 0.28]);
      gl.uniform1f(viewer.lineLocs.uPointSize, 1.0);
      gl.enable(gl.BLEND);
      gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);
      gl.bindVertexArray(viewer.gridVAO);
      gl.drawArrays(gl.LINES, 0, viewer.gridVertexCount);
      gl.bindVertexArray(null);
      gl.disable(gl.BLEND);

      if (!entry || entry.status !== 'ready' || !entry.data) {
        viewer.lastStats.loaded = false;
        viewer.lastStats.file = url.split('/').pop();
        viewer.lastStats.byteLength = 0;
        viewer.lastStats.verts = 0;
        viewer.lastStats.tris = 0;
        viewer.lastStats.joints = 0;
        viewer.lastStats.materials = 0;
        viewer.lastStats.clips = 0;
        viewer.lastStats.heightM = 0;
        return true;
      }

      const model = entry.data;
      const poseEval = evaluateAnimation(model, state.pose, state.animClock || 0);
      const modelMatrix = mat4Identity();
      modelMatrix[0] = modelScale;
      modelMatrix[5] = modelScale;
      modelMatrix[10] = modelScale;

      drawModel(model, modelMatrix, viewProj, view, proj, eye, state, poseEval);

      // Render companion 32-panel ball orbiting/kicking beside the fighter
      if (state.category === 'FIGHTERS' && ballEntry && ballEntry.status === 'ready' && ballEntry.data) {
        const ballAng = (state.tick || 0) * 0.035;
        const kickDist = state.ballKickTimer > 0 ? (45 - state.ballKickTimer) * 0.045 : 0;
        const bx = Math.cos(ballAng) * (0.68 + kickDist);
        const by = Math.abs(Math.sin((state.tick || 0) * 0.08)) * 0.24 + kickDist * 0.35;
        const bz = Math.sin(ballAng) * (0.68 + kickDist);
        const ballMat = mat4Identity();
        ballMat[12] = bx; ballMat[13] = by; ballMat[14] = bz;
        const ballEval = evaluateAnimation(ballEntry.data, '', 0);
        drawModel(ballEntry.data, ballMat, viewProj, view, proj, eye, { ...state, mode: 'SHADED' }, ballEval);
      }

      viewer.lastStats = {
        loaded: true,
        file: url.split('/').pop(),
        byteLength: model.byteLength || 0,
        verts: model.totalVerts,
        tris: model.totalTris,
        joints: model.skins.length ? model.skins[0].joints.length : 0,
        materials: model.materials.length,
        clips: model.animations.size,
        heightM: model.bounds.size[1] || 0,
        curKf: poseEval.curKf,
        totalKf: poseEval.totalKf,
        fps: viewer.lastStats.fps
      };

      return true;
    }
  };

  // ==========================================================================
  // SAFWglArena: Real-Time 2.5D Playable Combat WebGL2 Renderer (TAB 06)
  // Renders P1 SK_*.glb + P2 SK_*.glb + Active SM_Stage_*.glb + 3D Balls
  // ==========================================================================
  const arena = {
    gl: null,
    canvas: null,
    meshProg: null,
    lineProg: null,
    meshLocs: {},
    lineLocs: {},
    whiteTex: null,
    anisoExt: null,
    maxAniso: 1,
    lineBuf: null,
    lineVAO: null,
    pitchVAO: null,
    pitchIndexCount: 0,
    pitchLinesVAO: null,
    pitchLinesCount: 0,
    shadowVAO: null,
    shadowVertCount: 0,
    modelCache: new Map(),
    ballUrl: '../Assets/Models3D/Props/SM_Ball_TruncatedIcosahedron_32Panels.glb',
    lastViewProj: new Float32Array(16),
    lastWidth: 1080,
    lastHeight: 460,
    lastStatus: {
      ready: false,
      p1Loaded: false,
      p2Loaded: false,
      stageLoaded: false,
      p1Clip: 'Idle_Breath',
      p2Clip: 'Idle_Breath',
      p1Tris: 0,
      p2Tris: 0
    }
  };

  function mat4FromYRotScaleTrans(tx, ty, tz, ryRad, sx, sy, sz) {
    const out = new Float32Array(16);
    const c = Math.cos(ryRad);
    const s = Math.sin(ryRad);
    out[0] = c * sx;  out[1] = 0;  out[2] = -s * sx; out[3] = 0;
    out[4] = 0;       out[5] = sy; out[6] = 0;       out[7] = 0;
    out[8] = s * sz;  out[9] = 0;  out[10] = c * sz; out[11] = 0;
    out[12] = tx;     out[13] = ty; out[14] = tz;    out[15] = 1;
    return out;
  }

  function buildArenaPitchBuffers(gl) {
    // 1. Striped procedural grass quad mesh (24 stripes x -18..+18, z -14..+6)
    const positions = [];
    const normals = [];
    const colors = [];
    const uvs = [];
    const joints = [];
    const weights = [];
    const indices = [];
    const stripes = 24;
    const xStart = -18.0, xEnd = 18.0;
    const stripeW = (xEnd - xStart) / stripes;
    let vOff = 0;

    for (let i = 0; i < stripes; i++) {
      const x0 = xStart + i * stripeW;
      const x1 = x0 + stripeW;
      const even = (i % 2 === 0);
      const col = even ? [0.16, 0.42, 0.19, 1.0] : [0.12, 0.34, 0.15, 1.0];

      const quad = [
        [x0, 0.0, 5.5],
        [x1, 0.0, 5.5],
        [x1, 0.0, -14.0],
        [x0, 0.0, -14.0]
      ];
      for (let k = 0; k < 4; k++) {
        positions.push(quad[k][0], quad[k][1], quad[k][2]);
        normals.push(0, 1, 0);
        colors.push(col[0], col[1], col[2], col[3]);
        uvs.push(k === 1 || k === 2 ? 1 : 0, k >= 2 ? 1 : 0);
        joints.push(0, 0, 0, 0);
        weights.push(1, 0, 0, 0);
      }
      indices.push(vOff, vOff + 1, vOff + 2, vOff, vOff + 2, vOff + 3);
      vOff += 4;
    }

    const vao = gl.createVertexArray();
    gl.bindVertexArray(vao);
    const pushAttr = (loc, arr, size) => {
      const buf = gl.createBuffer();
      gl.bindBuffer(gl.ARRAY_BUFFER, buf);
      gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(arr), gl.STATIC_DRAW);
      gl.enableVertexAttribArray(loc);
      gl.vertexAttribPointer(loc, size, gl.FLOAT, false, 0, 0);
    };
    pushAttr(0, positions, 3);
    pushAttr(1, normals, 3);
    pushAttr(2, colors, 4);
    pushAttr(3, joints, 4);
    pushAttr(4, weights, 4);
    pushAttr(5, uvs, 2);
    const ibo = gl.createBuffer();
    gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER, ibo);
    gl.bufferData(gl.ELEMENT_ARRAY_BUFFER, new Uint16Array(indices), gl.STATIC_DRAW);
    gl.bindVertexArray(null);
    arena.pitchVAO = vao;
    arena.pitchIndexCount = indices.length;

    // 2. White pitch chalk markings (touchlines, halfway line, center circle, penalty box arcs)
    const chalk = [
      // Midfield line & bounds
      0, 0.008, -10.0,  0, 0.008, 3.2,
      -8.5, 0.008, 2.2,  8.5, 0.008, 2.2,
      -8.5, 0.008, -9.5, 8.5, 0.008, -9.5,
      -4.5, 0.008, -3.5, -4.5, 0.008, 2.2,
      4.5, 0.008, -3.5,  4.5, 0.008, 2.2
    ];
    for (let s = 0; s < 32; s++) {
      const a0 = (s / 32) * Math.PI * 2;
      const a1 = ((s + 1) / 32) * Math.PI * 2;
      chalk.push(
        Math.cos(a0) * 1.45, 0.008, -2.5 + Math.sin(a0) * 1.15,
        Math.cos(a1) * 1.45, 0.008, -2.5 + Math.sin(a1) * 1.15
      );
    }
    const lineVao = gl.createVertexArray();
    gl.bindVertexArray(lineVao);
    const lBuf = gl.createBuffer();
    gl.bindBuffer(gl.ARRAY_BUFFER, lBuf);
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(chalk), gl.STATIC_DRAW);
    gl.enableVertexAttribArray(0);
    gl.vertexAttribPointer(0, 3, gl.FLOAT, false, 0, 0);
    gl.bindVertexArray(null);
    arena.pitchLinesVAO = lineVao;
    arena.pitchLinesCount = chalk.length / 3;

    // 3. Soft elliptical ground shadow disc (TRIANGLE_FAN unit circle)
    const segs = 24;
    const sPos = [0, 0.012, 0];
    const sNorm = [0, 1, 0];
    const sCol = [0.02, 0.03, 0.02, 0.65];
    const sUv = [0.5, 0.5];
    const sJnt = [0, 0, 0, 0];
    const sWgt = [1, 0, 0, 0];
    for (let i = 0; i <= segs; i++) {
      const a = (i / segs) * Math.PI * 2;
      sPos.push(Math.cos(a) * 0.48, 0.012, Math.sin(a) * 0.30);
      sNorm.push(0, 1, 0);
      sCol.push(0.02, 0.03, 0.02, 0.0);
      sUv.push(0.5, 0.5);
      sJnt.push(0, 0, 0, 0);
      sWgt.push(1, 0, 0, 0);
    }
    const sVao = gl.createVertexArray();
    gl.bindVertexArray(sVao);
    pushAttr(0, sPos, 3);
    pushAttr(1, sNorm, 3);
    pushAttr(2, sCol, 4);
    pushAttr(3, sJnt, 4);
    pushAttr(4, sWgt, 4);
    pushAttr(5, sUv, 2);
    gl.bindVertexArray(null);
    arena.shadowVAO = sVao;
    arena.shadowVertCount = segs + 2;
  }

  function resolveFighterClipAndClock(model, actor, matchEnded, isWinner) {
    const pickClip = (candidates) => {
      for (let i = 0; i < candidates.length; i++) {
        if (model.animations.has(candidates[i])) return candidates[i];
      }
      return model.animations.keys().next().value || 'Idle_Breath';
    };

    if (actor.state === 'KO') {
      return { clip: pickClip(['Mocap_KO_Knockdown', 'Mocap_Hitstun_Knockback', 'Idle_Breath']), frame: actor.stateFrame, loop: false };
    }
    if (matchEnded && isWinner) {
      return { clip: pickClip(['Victory_Pose', 'Idle_Breath']), frame: actor.stateFrame || 0, loop: true };
    }

    switch (actor.state) {
      case 'WALK_F':
        return { clip: pickClip(['Mocap_Walk_Forward', 'Dash_Forward', 'Idle_Breath']), frame: actor.stateFrame, loop: true };
      case 'WALK_B':
        return { clip: pickClip(['Mocap_Backdash_Dodge', 'Mocap_Walk_Forward', 'Idle_Breath']), frame: actor.stateFrame, loop: true };
      case 'DASH_F':
        return { clip: pickClip(['Dash_Forward', 'Mocap_Walk_Forward']), frame: actor.stateFrame * 1.4, loop: true };
      case 'DASH_B':
        return { clip: pickClip(['Mocap_Backdash_Dodge', 'Idle_Breath']), frame: actor.stateFrame * 1.3, loop: false };
      case 'CROUCH':
        return { clip: pickClip(['Mocap_Crouch_Guard', 'Mocap_Block_Guard', 'Idle_Breath']), frame: actor.stateFrame || 12, loop: false };
      case 'JUMP':
        return { clip: pickClip(['Special_Chilena', 'Anim_623HP_BicycleKick', 'Idle_Breath']), frame: Math.min(28, actor.stateFrame * 1.2), loop: false };
      case 'BLOCKSTUN':
      case 'PARRY':
        return { clip: pickClip(['Mocap_Block_Guard', 'Anim_Idle']), frame: actor.stateFrame, loop: false };
      case 'HITSTUN':
        return { clip: pickClip(['Mocap_Hitstun_Knockback', 'Idle_Breath']), frame: actor.stateFrame * 1.3, loop: false };
      case 'STARTUP':
      case 'ACTIVE':
      case 'RECOVERY': {
        const mv = actor.activeMoveKey || 'LP';
        const mapMove = {
          LP: ['Anim_5LP_Jab4f', 'Kick_High'],
          MP: ['Kick_High', 'Anim_5LP_Jab4f'],
          HP: ['Kick_High', 'Anim_623HP_BicycleKick'],
          SK: ['Anim_236SK_Shot', 'Kick_High'],
          GB: ['Mocap_Block_Guard'],
          SP_236: ['Anim_236SK_Shot', 'Kick_High'],
          SP_623: ['Anim_623HP_BicycleKick', 'Special_Chilena'],
          SP_41236: ['Anim_214SK_Scorpion', 'Special_Chilena'],
          SUPER_1: ['Mocap_Super_Potrero', 'Special_Chilena'],
          ULT_3: ['Special_Chilena', 'Mocap_Super_Potrero']
        };
        return { clip: pickClip(mapMove[mv] || ['Kick_High', 'Idle_Breath']), frame: actor.stateFrame * 1.35, loop: false };
      }
      default:
        return { clip: pickClip(['Idle_Breath', 'Anim_Idle']), frame: actor.stateFrame || 0, loop: true };
    }
  }

  const SAFWglArena = {
    init(canvas) {
      if (!canvas) return false;
      try {
        const probe = document.createElement('canvas');
        const probeGl = probe.getContext('webgl2');
        if (!probeGl || !(probeGl instanceof WebGL2RenderingContext)) return false;
        const tMesh = createProgram(probeGl, MESH_VERT_SRC, MESH_FRAG_SRC);
        const tLine = createProgram(probeGl, LINE_VERT_SRC, LINE_FRAG_SRC);
        probeGl.deleteProgram(tMesh);
        probeGl.deleteProgram(tLine);
        const loseExt = probeGl.getExtension('WEBGL_lose_context');
        if (loseExt) loseExt.loseContext();

        const gl = canvas.getContext('webgl2', { antialias: true, alpha: false, preserveDrawingBuffer: false });
        if (!gl || !(gl instanceof WebGL2RenderingContext) || gl.isContextLost()) return false;

        arena.gl = gl;
        arena.canvas = canvas;
        arena.meshProg = createProgram(gl, MESH_VERT_SRC, MESH_FRAG_SRC);
        arena.lineProg = createProgram(gl, LINE_VERT_SRC, LINE_FRAG_SRC);

        [
          'uModel', 'uView', 'uProj', 'uHasSkin', 'uJointMatrices', 'uRenderMode',
          'uWindPct', 'uTime', 'uSmearScale', 'uPrimIndex', 'uCameraPos',
          'uBaseColor', 'uEmissive', 'uMetallic', 'uRoughness',
          'uHasVertexColor', 'uBaseColorTex', 'uHasBaseColorTex',
          'uLightingMode', 'uModelHeight'
        ].forEach((name) => {
          arena.meshLocs[name] = gl.getUniformLocation(arena.meshProg, name);
        });

        ['uMVP', 'uColor', 'uPointSize'].forEach((name) => {
          arena.lineLocs[name] = gl.getUniformLocation(arena.lineProg, name);
        });

        arena.whiteTex = createWhiteTexture(gl);
        arena.anisoExt = gl.getExtension('EXT_texture_filter_anisotropic');
        arena.maxAniso = arena.anisoExt ? gl.getParameter(arena.anisoExt.MAX_TEXTURE_MAX_ANISOTROPY_EXT) : 1;

        const lineVao = gl.createVertexArray();
        gl.bindVertexArray(lineVao);
        const lBuf = gl.createBuffer();
        gl.bindBuffer(gl.ARRAY_BUFFER, lBuf);
        gl.enableVertexAttribArray(0);
        gl.vertexAttribPointer(0, 3, gl.FLOAT, false, 0, 0);
        gl.bindVertexArray(null);
        arena.lineVAO = lineVao;
        arena.lineBuf = lBuf;

        buildArenaPitchBuffers(gl);
        arena.lastStatus.ready = true;
        return true;
      } catch (err) {
        console.warn('[SAFWglArena] WebGL2 Arena initialization fallback:', err);
        arena.gl = null;
        arena.lastStatus.ready = false;
        return false;
      }
    },

    isReady() {
      return Boolean(arena.gl && arena.gl instanceof WebGL2RenderingContext && !arena.gl.isContextLost());
    },

    preload(urls) {
      if (!this.isReady() || !Array.isArray(urls)) return;
      requestModel(arena.ballUrl, arena);
      urls.forEach((u) => { if (u) requestModel(u, arena); });
    },

    getStatus() {
      return arena.lastStatus;
    },

    projectToCanvas(wx, wy, wz) {
      const vp = arena.lastViewProj;
      const cx = vp[0] * wx + vp[4] * wy + vp[8] * wz + vp[12];
      const cy = vp[1] * wx + vp[5] * wy + vp[9] * wz + vp[13];
      const cw = vp[3] * wx + vp[7] * wy + vp[11] * wz + vp[15];
      if (Math.abs(cw) < 1e-5) return [arena.lastWidth * 0.5, arena.lastHeight * 0.5];
      const ndcX = cx / cw;
      const ndcY = cy / cw;
      return [
        (ndcX * 0.5 + 0.5) * arena.lastWidth,
        (0.5 - ndcY * 0.5) * arena.lastHeight
      ];
    },

    renderFrame(spec) {
      const gl = arena.gl;
      if (!gl) return false;

      const w = arena.canvas.width;
      const h = arena.canvas.height;
      arena.lastWidth = w;
      arena.lastHeight = h;
      gl.viewport(0, 0, w, h);
      gl.enable(gl.DEPTH_TEST);
      gl.disable(gl.CULL_FACE);

      const isSfumato = spec.lighting === 'SFUMATO';
      if (spec.impactInkFrames > 0) {
        const flash = spec.impactInkFrames % 2 === 0;
        gl.clearColor(flash ? 0.92 : 0.03, flash ? 0.84 : 0.04, flash ? 0.58 : 0.07, 1.0);
      } else if (isSfumato) {
        gl.clearColor(spec.inZoneB ? 0.14 : 0.12, spec.inZoneB ? 0.07 : 0.11, spec.inZoneB ? 0.04 : 0.08, 1.0);
      } else {
        gl.clearColor(spec.inZoneB ? 0.10 : 0.03, spec.inZoneB ? 0.04 : 0.07, spec.inZoneB ? 0.12 : 0.14, 1.0);
      }
      gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);

      const p1Wx = (spec.p1.x - 540) / 145.0;
      const p1Wy = Math.max(0, -spec.p1.y / 145.0);
      const p2Wx = (spec.p2.x - 540) / 145.0;
      const p2Wy = Math.max(0, -spec.p2.y / 145.0);

      const midX = (p1Wx + p2Wx) * 0.5;
      const dist = Math.abs(p1Wx - p2Wx);
      const camX = midX * 0.35 + ((spec.shakeX || 0) / 160.0);
      const camY = 1.48 + ((spec.shakeY || 0) / 160.0);
      const camZ = Math.min(7.8, Math.max(4.6, 4.35 + dist * 0.42));
      const eye = [camX, camY, camZ];
      const target = [midX * 0.52, 0.98, -0.6];

      const proj = new Float32Array(16);
      const view = new Float32Array(16);
      const viewProj = new Float32Array(16);
      mat4Perspective(proj, (38 * Math.PI) / 180, w / Math.max(1, h), 0.1, 200.0);
      mat4LookAt(view, eye, target, [0, 1, 0]);
      mat4Multiply(viewProj, proj, view);
      arena.lastViewProj.set(viewProj);

      // 1. Render 3D Grass Pitch + Chalk Markings
      const identityMat = mat4Identity();
      gl.useProgram(arena.meshProg);
      gl.uniformMatrix4fv(arena.meshLocs.uModel, false, identityMat);
      gl.uniformMatrix4fv(arena.meshLocs.uView, false, view);
      gl.uniformMatrix4fv(arena.meshLocs.uProj, false, proj);
      gl.uniform3fv(arena.meshLocs.uCameraPos, eye);
      gl.uniform1i(arena.meshLocs.uHasSkin, 0);
      gl.uniform1i(arena.meshLocs.uLightingMode, isSfumato ? 0 : 1);
      gl.uniform1i(arena.meshLocs.uRenderMode, 0);
      gl.uniform1i(arena.meshLocs.uHasBaseColorTex, 0);
      gl.uniform1i(arena.meshLocs.uHasVertexColor, 1);
      gl.uniform4fv(arena.meshLocs.uBaseColor, isSfumato ? [0.92, 0.88, 0.72, 1.0] : [0.85, 1.0, 0.92, 1.0]);
      gl.uniform3fv(arena.meshLocs.uEmissive, [0, 0, 0]);
      gl.uniform1f(arena.meshLocs.uMetallic, 0.0);
      gl.uniform1f(arena.meshLocs.uRoughness, 0.88);
      gl.bindTexture(gl.TEXTURE_2D, arena.whiteTex);
      gl.bindVertexArray(arena.pitchVAO);
      gl.drawElements(gl.TRIANGLES, arena.pitchIndexCount, gl.UNSIGNED_SHORT, 0);
      gl.bindVertexArray(null);

      gl.useProgram(arena.lineProg);
      gl.uniformMatrix4fv(arena.lineLocs.uMVP, false, viewProj);
      gl.uniform4fv(arena.lineLocs.uColor, isSfumato ? [0.94, 0.87, 0.68, 0.78] : [0.95, 0.98, 1.0, 0.85]);
      gl.bindVertexArray(arena.pitchLinesVAO);
      gl.drawArrays(gl.LINES, 0, arena.pitchLinesCount);
      gl.bindVertexArray(null);

      // 2. Render 3D Stadium Backdrop (`SM_Stage_*.glb`)
      const stageEntry = spec.stageGlbUrl ? requestModel(spec.stageGlbUrl, arena) : null;
      if (stageEntry && stageEntry.status === 'ready' && stageEntry.data) {
        const sMod = stageEntry.data;
        const sScale = 24.0 / Math.max(20.0, sMod.bounds.maxSpan || 60.0);
        const sMat = mat4FromYRotScaleTrans(0.0, -0.04, -12.5, 0.0, sScale, sScale, sScale);
        const sEval = evaluateAnimation(sMod, '', 0, false);
        drawModel(sMod, sMat, viewProj, view, proj, eye, { mode: 'SHADED', lighting: spec.lighting, tick: spec.clockFrames || 0 }, sEval, arena, null);
        arena.lastStatus.stageLoaded = true;
      } else {
        arena.lastStatus.stageLoaded = false;
      }

      // 3. Soft Ground Shadows beneath P1 & P2
      gl.enable(gl.BLEND);
      gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);
      gl.depthMask(false);
      gl.useProgram(arena.meshProg);
      gl.uniform1i(arena.meshLocs.uHasSkin, 0);
      gl.uniform1i(arena.meshLocs.uHasBaseColorTex, 0);
      gl.uniform1i(arena.meshLocs.uHasVertexColor, 1);
      gl.uniform4fv(arena.meshLocs.uBaseColor, [0.02, 0.02, 0.02, 0.58]);
      gl.uniform3fv(arena.meshLocs.uEmissive, [0, 0, 0]);
      gl.bindTexture(gl.TEXTURE_2D, arena.whiteTex);
      gl.bindVertexArray(arena.shadowVAO);
      [[p1Wx, 0.08], [p2Wx, -0.08]].forEach(([sx, sz]) => {
        const shMat = mat4FromYRotScaleTrans(sx, 0.0, sz, 0, 1.0, 1.0, 1.0);
        gl.uniformMatrix4fv(arena.meshLocs.uModel, false, shMat);
        gl.drawArrays(gl.TRIANGLE_FAN, 0, arena.shadowVertCount);
      });
      gl.bindVertexArray(null);
      gl.depthMask(true);
      gl.disable(gl.BLEND);

      // 4. Render 3D Fighter P1 & Fighter P2
      const renderActor = (actor, wx, wy, wz, isP1) => {
        const entry = actor.glbUrl ? requestModel(actor.glbUrl, arena) : null;
        if (!entry || entry.status !== 'ready' || !entry.data) return { loaded: false, clip: 'Loading', tris: 0 };
        const mod = entry.data;
        const isWinner = spec.matchEnded && ((isP1 && spec.winnerIsP1) || (!isP1 && !spec.winnerIsP1));
        const animPick = resolveFighterClipAndClock(mod, actor, spec.matchEnded, isWinner);
        const poseEval = evaluateAnimation(mod, animPick.clip, animPick.frame, animPick.loop);
        const ry = actor.facingRight ? (Math.PI * 0.5) : (-Math.PI * 0.5);
        const modMat = mat4FromYRotScaleTrans(wx, wy, wz, ry, 1.0, 1.0, 1.0);
        const hitEm = actor.state === 'HITSTUN' ? [0.45, 0.08, 0.06] : (actor.state === 'PARRY' ? [0.05, 0.38, 0.45] : null);
        drawModel(mod, modMat, viewProj, view, proj, eye, {
          mode: 'SHADED',
          lighting: spec.lighting,
          windPct: 75,
          tick: spec.clockFrames || 0,
          smearScale: actor.state === 'ACTIVE' ? 1.12 : 1.0
        }, poseEval, arena, hitEm);
        return { loaded: true, clip: animPick.clip, tris: mod.totalTris };
      };

      const p1Res = renderActor(spec.p1, p1Wx, p1Wy, 0.06, true);
      const p2Res = renderActor(spec.p2, p2Wx, p2Wy, -0.06, false);

      // 5. Render 3D Match Ball Projectiles (`SM_Ball_TruncatedIcosahedron_32Panels.glb`)
      const ballEntry = requestModel(arena.ballUrl, arena);
      if (ballEntry && ballEntry.status === 'ready' && ballEntry.data && Array.isArray(spec.projectiles)) {
        const bMod = ballEntry.data;
        const bEval = evaluateAnimation(bMod, '', 0, false);
        const spin = ((spec.clockFrames || 0) * 0.25);
        spec.projectiles.forEach((pr) => {
          const bwx = (pr.x - 540) / 145.0;
          const bwy = Math.max(0.18, (390 - pr.y) / 145.0);
          const bScale = 1.65;
          const bMat = mat4FromYRotScaleTrans(bwx, bwy, 0.0, spin * (pr.vx >= 0 ? 1 : -1), bScale, bScale, bScale);
          drawModel(bMod, bMat, viewProj, view, proj, eye, { mode: 'SHADED', lighting: spec.lighting, tick: spec.clockFrames || 0 }, bEval, arena, [0.35, 0.28, 0.05]);
        });
      }

      arena.lastStatus = {
        ready: true,
        p1Loaded: p1Res.loaded,
        p2Loaded: p2Res.loaded,
        stageLoaded: arena.lastStatus.stageLoaded,
        p1Clip: p1Res.clip,
        p2Clip: p2Res.clip,
        p1Tris: p1Res.tris,
        p2Tris: p2Res.tris
      };
      return true;
    }
  };

  global.SAFWglViewer = SAFWglViewer;
  global.SAFWglArena = SAFWglArena;
})(window);
