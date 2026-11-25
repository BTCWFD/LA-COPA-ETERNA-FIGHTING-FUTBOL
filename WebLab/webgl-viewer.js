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
    gl_Position = uProj * uView * world;
  }`;

  const MESH_FRAG_SRC = `#version 300 es
  precision highp float;

  in vec3 vWorldPos;
  in vec3 vNormal;
  in vec4 vColor;
  in vec3 vLocalPos;

  uniform vec3 uCameraPos;
  uniform vec4 uBaseColor;
  uniform vec3 uEmissive;
  uniform float uMetallic;
  uniform float uRoughness;
  uniform int uHasVertexColor;
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

    vec4 vertCol = uHasVertexColor == 1 ? vColor : vec4(1.0);
    vec3 albedo = uBaseColor.rgb * vertCol.rgb;

    if (uRenderMode == 2) {
      float normY = clamp(vLocalPos.y / max(0.4, uModelHeight), 0.0, 1.0);
      float freedom = uHasSkin == 1 ? clamp(1.0 - normY * 0.95, 0.0, 1.0) : clamp(abs(vLocalPos.x) / max(1.0, uModelHeight), 0.0, 1.0);
      vec3 heat = clothHeatmap(freedom);
      float diff = max(dot(N, normalize(vec3(0.5, 0.85, 0.4))), 0.0) * 0.65 + 0.35;
      fragColor = vec4(heat * diff + vec3(0.08) * pow(1.0 - ndotv, 2.5), 1.0);
      return;
    }

    vec3 keyDir;
    vec3 keyColor;
    vec3 fillDir = normalize(vec3(-0.6, 0.35, -0.7));
    vec3 fillColor;
    vec3 ambientColor;
    vec3 rimColor;
    float rimPow;

    if (uLightingMode == 0) {
      // Renacimiento Sfumato (Da Vinci golden-amber chiaroscuro + olive/ochre ambient)
      keyDir = normalize(vec3(0.65, 0.82, 0.55));
      keyColor = vec3(1.18, 0.96, 0.66);
      fillColor = vec3(0.24, 0.28, 0.16);
      ambientColor = vec3(0.20, 0.17, 0.10);
      rimColor = vec3(1.0, 0.86, 0.52);
      rimPow = 2.6;
    } else {
      // Street-Ink AAA (Stadium floodlight + high-contrast cyan/white rim)
      keyDir = normalize(vec3(-0.45, 0.90, 0.65));
      keyColor = vec3(1.05, 1.12, 1.25);
      fillColor = vec3(0.14, 0.24, 0.38);
      ambientColor = vec3(0.10, 0.14, 0.22);
      rimColor = vec3(0.15, 0.92, 1.0);
      rimPow = 2.2;
    }

    float nDotL = max(dot(N, keyDir), 0.0);
    float nDotFill = max(dot(N, fillDir), 0.0);
    vec3 H = normalize(keyDir + V);
    float specPower = mix(84.0, 10.0, clamp(uRoughness, 0.05, 1.0));
    float spec = pow(max(dot(N, H), 0.0), specPower) * mix(0.28, 0.85, uMetallic);
    float rim = pow(1.0 - ndotv, rimPow);

    // Subtle stepped ink shadow accent in Street-Ink or SMEAR mode
    if (uLightingMode == 1 || uRenderMode == 3) {
      nDotL = mix(nDotL, floor(nDotL * 3.5 + 0.35) / 3.5, 0.45);
    }

    vec3 lit =
      albedo * (ambientColor + keyColor * nDotL + fillColor * nDotFill) +
      keyColor * spec +
      rimColor * rim * 0.58 +
      uEmissive;

    // Gentle tone mapping + gamma feel
    lit = lit / (lit + vec3(0.65));
    lit = pow(max(lit, vec3(0.0)), vec3(0.92));

    float alpha = uRenderMode == 1 ? 0.24 : uBaseColor.a;
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
      verts: 0,
      tris: 0,
      joints: 0,
      clips: 0,
      curKf: 1,
      totalKf: 1,
      fps: 60.0
    },
    _lastFrameTime: 0
  };

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

  function uploadGLBToGPU(gl, parsed) {
    const { gltf, binBuffer } = parsed;
    const materials = (gltf.materials || []).map((m) => {
      const pbr = m.pbrMetallicRoughness || {};
      return {
        name: m.name || 'Mat',
        baseColorFactor: pbr.baseColorFactor ? Float32Array.from(pbr.baseColorFactor) : new Float32Array([0.85, 0.85, 0.85, 1.0]),
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
      meshes,
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

  function requestModel(url) {
    if (!url) return null;
    const cached = viewer.modelCache.get(url);
    if (cached) return cached;

    const entry = { status: 'loading', data: null };
    viewer.modelCache.set(url, entry);

    fetch(url)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.arrayBuffer();
      })
      .then((buf) => {
        const parsed = parseGLB(buf);
        entry.data = uploadGLBToGPU(viewer.gl, parsed);
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
  function evaluateAnimation(model, clipName, animClockFrames) {
    const nodeCount = model.nodes.length;
    const localT = model.nodes.map((n) => Float32Array.from(n.translation));
    const localR = model.nodes.map((n) => Float32Array.from(n.rotation));
    const localS = model.nodes.map((n) => Float32Array.from(n.scale));

    const clip = model.animations.get(clipName) || model.animations.values().next().value || null;
    let curKf = 1;
    let totalKf = 1;

    if (clip && clip.duration > 0) {
      const timeSecRaw = animClockFrames / 60.0;
      const t = timeSecRaw % clip.duration;
      const firstSmp = clip.samplers[0];
      if (firstSmp && firstSmp.input.length > 0) {
        totalKf = firstSmp.input.length;
        curKf = (Math.floor(animClockFrames) % totalKf) + 1;
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
  function drawLines(mvp, vertsArray, color, mode, pointSize = 5.0) {
    const gl = viewer.gl;
    if (!vertsArray || vertsArray.length === 0) return;
    gl.useProgram(viewer.lineProg);
    gl.uniformMatrix4fv(viewer.lineLocs.uMVP, false, mvp);
    gl.uniform4fv(viewer.lineLocs.uColor, color);
    gl.uniform1f(viewer.lineLocs.uPointSize, pointSize);

    gl.bindVertexArray(viewer.lineVAO);
    gl.bindBuffer(gl.ARRAY_BUFFER, viewer.lineBuf);
    gl.bufferData(gl.ARRAY_BUFFER, vertsArray instanceof Float32Array ? vertsArray : new Float32Array(vertsArray), gl.DYNAMIC_DRAW);
    gl.drawArrays(mode, 0, vertsArray.length / 3);
    gl.bindVertexArray(null);
  }

  function drawModel(model, modelMatrix, viewProj, view, proj, cameraPos, state, poseEval) {
    const gl = viewer.gl;
    const renderModeMap = { SHADED: 0, SKELETON: 1, CLOTH: 2, SMEAR: 3 };
    const rMode = renderModeMap[state.mode] ?? 0;
    const lMode = state.lighting === 'SFUMATO' ? 0 : 1;

    gl.useProgram(viewer.meshProg);
    gl.uniformMatrix4fv(viewer.meshLocs.uView, false, view);
    gl.uniformMatrix4fv(viewer.meshLocs.uProj, false, proj);
    gl.uniform3fv(viewer.meshLocs.uCameraPos, cameraPos);
    gl.uniform1i(viewer.meshLocs.uLightingMode, lMode);
    gl.uniform1i(viewer.meshLocs.uRenderMode, rMode);
    gl.uniform1f(viewer.meshLocs.uWindPct, (state.windPct || 0) / 100);
    gl.uniform1f(viewer.meshLocs.uTime, (state.tick || 0) / 60.0);
    gl.uniform1f(viewer.meshLocs.uSmearScale, state.smearScale || 1.0);
    gl.uniform1f(viewer.meshLocs.uModelHeight, model.bounds.size[1] || 1.8);

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
        gl.uniformMatrix4fv(viewer.meshLocs.uJointMatrices, false, jointBuffer);
      } else {
        mat4Multiply(fullModel, modelMatrix, nodeWorld);
      }

      gl.uniform1i(viewer.meshLocs.uHasSkin, hasSkin);
      gl.uniformMatrix4fv(viewer.meshLocs.uModel, false, fullModel);

      if (rMode === 1) {
        gl.enable(gl.BLEND);
        gl.blendFunc(gl.SRC_ALPHA, gl.ONE_MINUS_SRC_ALPHA);
        gl.depthMask(false);
      }

      for (let p = 0; p < mesh.primitives.length; p++) {
        const prim = mesh.primitives[p];
        const mat = model.materials[prim.materialIndex] || {
          baseColorFactor: new Float32Array([0.85, 0.85, 0.85, 1.0]),
          emissiveFactor: new Float32Array([0, 0, 0]),
          metallicFactor: 0.1,
          roughnessFactor: 0.6
        };

        gl.uniform4fv(viewer.meshLocs.uBaseColor, mat.baseColorFactor);
        gl.uniform3fv(viewer.meshLocs.uEmissive, mat.emissiveFactor);
        gl.uniform1f(viewer.meshLocs.uMetallic, mat.metallicFactor);
        gl.uniform1f(viewer.meshLocs.uRoughness, mat.roughnessFactor);
        gl.uniform1i(viewer.meshLocs.uHasVertexColor, prim.hasVertexColor);
        gl.uniform1i(viewer.meshLocs.uPrimIndex, prim.primIndex);

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
        gl.useProgram(viewer.lineProg);
        gl.uniformMatrix4fv(viewer.lineLocs.uMVP, false, mvp);
        gl.uniform4fv(viewer.lineLocs.uColor, hasSkin ? [0.0, 0.90, 1.0, 0.32] : [0.96, 0.77, 0.32, 0.55]);
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
      drawLines(mvp, boneLines, [0.96, 0.77, 0.32, 1.0], gl.LINES);
      drawLines(mvp, jointPts, [0.0, 0.90, 1.0, 1.0], gl.POINTS, 6.0);
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
        const gl = canvas.getContext('webgl2', { antialias: true, alpha: false, preserveDrawingBuffer: false });
        if (!gl || !(gl instanceof WebGL2RenderingContext)) {
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
          'uHasVertexColor', 'uLightingMode', 'uModelHeight'
        ].forEach((name) => {
          viewer.meshLocs[name] = gl.getUniformLocation(viewer.meshProg, name);
        });

        ['uMVP', 'uColor', 'uPointSize'].forEach((name) => {
          viewer.lineLocs[name] = gl.getUniformLocation(viewer.lineProg, name);
        });

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
      return Boolean(viewer.gl && viewer.gl instanceof WebGL2RenderingContext);
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
        verts: model.totalVerts,
        tris: model.totalTris,
        joints: model.skins.length ? model.skins[0].joints.length : 0,
        clips: model.animations.size,
        curKf: poseEval.curKf,
        totalKf: poseEval.totalKf,
        fps: viewer.lastStats.fps
      };

      return true;
    }
  };

  global.SAFWglViewer = SAFWglViewer;
})(window);
