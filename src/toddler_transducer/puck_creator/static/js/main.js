import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { TextGeometry } from 'three/addons/geometries/TextGeometry.js';
import { FontLoader } from 'three/addons/loaders/FontLoader.js';
import { STLLoader } from 'three/addons/loaders/STLLoader.js';

let scene, camera, renderer, controls;
let puckGroup = null;
let font = null;
let pendingUpdate = null;
let uploadPath = null;
let uploadMeshUrl = null;
let uploadMeshGeo = null;
let aiImagePath = null;
let aiImageDataUrl = null;
let aiMeshGeo = null;
let aiMeshMaterial = null;
let aiMeshId = null;
let aiRawStlUrl = null;

const FONT_URL = 'https://cdn.jsdelivr.net/npm/three@0.160.0/examples/fonts/helvetiker_regular.typeface.json';

function init() {
    const viewport = document.getElementById('viewport');
    const rect = viewport.getBoundingClientRect();

    scene = new THREE.Scene();
    scene.background = new THREE.Color(0x1a1a2e);

    camera = new THREE.PerspectiveCamera(40, rect.width / rect.height, 1, 500);
    camera.position.set(60, 45, 80);
    camera.lookAt(0, 0, 0);

    renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(rect.width, rect.height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    viewport.appendChild(renderer.domElement);

    controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.1;
    controls.target.set(0, 0, 0);
    controls.update();

    const ambientLight = new THREE.AmbientLight(0x404060, 0.6);
    scene.add(ambientLight);

    const dirLight = new THREE.DirectionalLight(0xffffff, 1.2);
    dirLight.position.set(30, 50, 40);
    dirLight.castShadow = true;
    scene.add(dirLight);

    const fillLight = new THREE.DirectionalLight(0x8888ff, 0.4);
    fillLight.position.set(-30, 20, -40);
    scene.add(fillLight);

    const backLight = new THREE.DirectionalLight(0xffffff, 0.3);
    backLight.position.set(0, 10, -50);
    scene.add(backLight);

    const gridHelper = new THREE.GridHelper(80, 20, 0x4444aa, 0x333366);
    scene.add(gridHelper);

    const ringGeometry = new THREE.RingGeometry(24, 25, 64);
    const ringMaterial = new THREE.MeshBasicMaterial({
        color: 0x444488,
        side: THREE.DoubleSide,
        transparent: true,
        opacity: 0.15,
    });
    const guideRing = new THREE.Mesh(ringGeometry, ringMaterial);
    guideRing.rotation.x = -Math.PI / 2;
    guideRing.position.y = -0.01;
    scene.add(guideRing);

    window.addEventListener('resize', onResize);

    const loader = new FontLoader();
    loader.load(FONT_URL, (f) => {
        font = f;
        updatePreview();
    }, undefined, () => {
        font = null;
    });

    bindControls();
    updatePreview();
}

function onResize() {
    const viewport = document.getElementById('viewport');
    const rect = viewport.getBoundingClientRect();
    camera.aspect = rect.width / rect.height;
    camera.updateProjectionMatrix();
    renderer.setSize(rect.width, rect.height);
}

function createPreviewMesh() {
    const group = new THREE.Group();

    const baseDiam = parseFloat(document.getElementById('base_diameter').value);
    const baseThick = parseFloat(document.getElementById('base_thickness').value);
    const holeDiam = parseFloat(document.getElementById('hole_diameter').value);
    const topType = document.getElementById('top_type').value;

    const baseRadius = baseDiam / 2;
    const halfThick = baseThick / 2;

    const baseGeo = new THREE.CylinderGeometry(baseRadius, baseRadius, baseThick, 64);
    const baseMat = new THREE.MeshPhysicalMaterial({
        color: 0x4a90d9,
        metalness: 0.1,
        roughness: 0.4,
        clearcoat: 0.1,
    });
    const baseMesh = new THREE.Mesh(baseGeo, baseMat);
    baseMesh.castShadow = true;
    group.add(baseMesh);

    if (holeDiam > 0 && holeDiam < baseDiam) {
        const holeRadius = holeDiam / 2;
        const holeHeight = parseFloat(document.getElementById('hole_height').value);
        const bottomOffset = parseFloat(document.getElementById('hole_bottom_offset').value);
        if (holeHeight > 0.1) {
            const cavityCenterY = -halfThick + bottomOffset + holeHeight / 2;
            const cavityGeo = new THREE.CylinderGeometry(holeRadius, holeRadius, holeHeight * 1.05, 32);
            const cavityMat = new THREE.MeshPhysicalMaterial({
                color: 0x222244,
                metalness: 0.3,
                roughness: 0.8,
            });
            const cavityMesh = new THREE.Mesh(cavityGeo, cavityMat);
            cavityMesh.position.y = cavityCenterY;
            group.add(cavityMesh);
        }
    }

    if (topType === 'shape') {
        const shapeType = document.getElementById('shape_type').value;
        const size = parseFloat(document.getElementById('shape_size').value);
        const height = parseFloat(document.getElementById('shape_height').value);

        let topGeo;
        switch (shapeType) {
            case 'cube':
                topGeo = new THREE.BoxGeometry(size, height, size);
                break;
            case 'sphere':
                topGeo = new THREE.SphereGeometry(size * 0.5, 24, 24);
                break;
            case 'cylinder':
                topGeo = new THREE.CylinderGeometry(size * 0.5, size * 0.5, height, 24);
                break;
            case 'cone':
                topGeo = new THREE.ConeGeometry(size * 0.5, height, 24);
                break;
            case 'torus':
                topGeo = new THREE.TorusGeometry(size * 0.5, height * 0.3, 16, 24);
                break;
            case 'heart':
                topGeo = createHeartShape(size * 0.5, height);
                break;
            case 'star':
                topGeo = createStarShape(size * 0.5, height);
                break;
            default:
                topGeo = new THREE.BoxGeometry(size, height, size);
        }

        const topMat = new THREE.MeshPhysicalMaterial({
            color: 0xe67e22,
            metalness: 0.3,
            roughness: 0.3,
        });
        const topMesh = new THREE.Mesh(topGeo, topMat);
        topMesh.castShadow = true;

        const bbox = new THREE.Box3().setFromObject(topMesh);
        const topHeight = bbox.max.y - bbox.min.y;
        topMesh.position.y = halfThick + topHeight / 2;
        group.add(topMesh);
    } else if (topType === 'text') {
        const text = document.getElementById('text_content').value || '?';
        const textH = parseFloat(document.getElementById('text_height').value);
        const fontSize = parseFloat(document.getElementById('font_size').value);

        if (font) {
            const textGeo = new TextGeometry(text, {
                font: font,
                size: fontSize * 0.15,
                height: textH,
                curveSegments: 6,
                bevelEnabled: true,
                bevelThickness: 0.5,
                bevelSize: 0.2,
                bevelSegments: 3,
            });
            textGeo.computeBoundingBox();
            const bbox = textGeo.boundingBox;
            const textWidth = bbox.max.x - bbox.min.x;
            const textDepth = bbox.max.z - bbox.min.z;

            const textMat = new THREE.MeshPhysicalMaterial({
                color: 0xe67e22,
                metalness: 0.3,
                roughness: 0.3,
            });
            const textMesh = new THREE.Mesh(textGeo, textMat);
            textMesh.castShadow = true;
            textMesh.position.x = -textWidth / 2;
            textMesh.position.z = -textDepth / 2;
            textMesh.position.y = halfThick + textH / 2;
            group.add(textMesh);
        } else {
            const placeholder = new THREE.Mesh(
                new THREE.BoxGeometry(fontSize * 0.8, textH, fontSize * 0.15),
                new THREE.MeshPhysicalMaterial({ color: 0xe67e22, metalness: 0.3, roughness: 0.3 })
            );
            placeholder.position.y = halfThick + textH / 2;
            group.add(placeholder);
        }
    } else if (topType === 'upload') {
        if (uploadMeshGeo) {
            const geo = uploadMeshGeo.clone();
            const mesh = new THREE.Mesh(geo, new THREE.MeshPhysicalMaterial({
                color: 0x2ecc71,
                metalness: 0.2,
                roughness: 0.4,
            }));
            mesh.castShadow = true;

            const scale = parseFloat(document.getElementById('upload_scale').value);
            const fx = document.getElementById('upload_flip_x').checked;
            const fy = document.getElementById('upload_flip_y').checked;
            const fz = document.getElementById('upload_flip_z').checked;
            const rotX = parseFloat(document.getElementById('upload_rotation_x').value);
            const rotY = parseFloat(document.getElementById('upload_rotation_y').value);
            const rotZ = parseFloat(document.getElementById('upload_rotation_z').value);

            mesh.scale.set(scale * (fx ? -1 : 1), scale * (fy ? -1 : 1), scale * (fz ? -1 : 1));
            mesh.rotation.set(rotX * Math.PI / 180, rotY * Math.PI / 180, rotZ * Math.PI / 180);

            const bbox = new THREE.Box3().setFromObject(mesh);
            const halfH = (bbox.max.y - bbox.min.y) / 2;
            const ox = parseFloat(document.getElementById('upload_offset_x').value);
            const oy = parseFloat(document.getElementById('upload_offset_y').value);
            const oz = parseFloat(document.getElementById('upload_offset_z').value);
            mesh.position.set(ox, halfThick + halfH + oz, oy);

            group.add(mesh);
        } else if (uploadPath) {
            const placeholder = new THREE.Mesh(
                new THREE.BoxGeometry(20, 10, 20),
                new THREE.MeshPhysicalMaterial({
                    color: 0x2ecc71,
                    metalness: 0.1,
                    roughness: 0.6,
                    transparent: true,
                    opacity: 0.3,
                })
            );
            placeholder.position.y = halfThick + 5;
            group.add(placeholder);
            const labelSprite = makeTextSprite('Loading...');
            labelSprite.position.y = halfThick + 15;
            group.add(labelSprite);
        }
    } else if (topType === 'ai_model') {
        if (aiMeshGeo) {
            const geo = aiMeshGeo.clone();
            const mesh = new THREE.Mesh(geo, aiMeshMaterial || new THREE.MeshPhysicalMaterial({
                color: 0xe67e22,
                metalness: 0.3,
                roughness: 0.3,
            }));
            mesh.castShadow = true;

            const scale = parseFloat(document.getElementById('ai_scale').value);
            const fx = document.getElementById('ai_flip_x').checked;
            const fy = document.getElementById('ai_flip_y').checked;
            const fz = document.getElementById('ai_flip_z').checked;
            const rotX = parseFloat(document.getElementById('ai_rotation_x').value);
            const rotY = parseFloat(document.getElementById('ai_rotation_y').value);
            const rotZ = parseFloat(document.getElementById('ai_rotation_z').value);

            mesh.scale.set(scale * (fx ? -1 : 1), scale * (fy ? -1 : 1), scale * (fz ? -1 : 1));
            mesh.rotation.set(rotX * Math.PI / 180, rotY * Math.PI / 180, rotZ * Math.PI / 180);

            const bbox = new THREE.Box3().setFromObject(mesh);
            const halfH = (bbox.max.y - bbox.min.y) / 2;
            const ox = parseFloat(document.getElementById('ai_offset_x').value);
            const oy = parseFloat(document.getElementById('ai_offset_y').value);
            const oz = parseFloat(document.getElementById('ai_offset_z').value);
            mesh.position.set(ox, halfThick + halfH + oz, oy);

            group.add(mesh);
        } else if (aiImageDataUrl) {
            const img = new Image();
            img.src = aiImageDataUrl;
            const aspect = img.naturalWidth / img.naturalHeight || 1;
            const planeW = 20;
            const planeH = planeW / aspect;
            const texture = new THREE.Texture(img);
            texture.needsUpdate = true;
            const planeGeo = new THREE.PlaneGeometry(planeW, planeH);
            const planeMat = new THREE.MeshBasicMaterial({
                map: texture,
                side: THREE.DoubleSide,
                transparent: true,
                depthWrite: false,
            });
            const plane = new THREE.Mesh(planeGeo, planeMat);
            plane.position.y = halfThick + 0.1;
            group.add(plane);

            const borderMat = new THREE.MeshBasicMaterial({
                color: 0x9b59b6,
                wireframe: false,
                transparent: true,
                opacity: 0.3,
                side: THREE.DoubleSide,
            });
            const border = new THREE.Mesh(
                new THREE.PlaneGeometry(planeW + 0.5, planeH + 0.5),
                borderMat
            );
            border.position.y = halfThick + 0.05;
            group.add(border);

            const label = makeTextSprite('AI: image loaded');
            label.position.y = halfThick + Math.max(planeH, 10) / 2 + 3;
            group.add(label);
        }
    }

    return group;
}

function createHeartShape(size, height) {
    const shape = new THREE.Shape();
    const x = size, y = size * 0.7;
    shape.moveTo(x, y + 0);
    shape.bezierCurveTo(x, y - 2, x * 1.5, y - 5, x * 2, y - 3);
    shape.bezierCurveTo(x * 2.5, y - 1, x * 2.5, y + 3, x * 2, y + 5);
    shape.bezierCurveTo(x * 1.5, y + 8, x, y + 7, x, y + 7);
    shape.bezierCurveTo(x, y + 7, x * 0.5, y + 8, 0, y + 5);
    shape.bezierCurveTo(-x * 0.5, y + 3, -x * 0.5, y - 1, 0, y - 3);
    shape.bezierCurveTo(x * 0.5, y - 5, x, y - 2, x, y + 0);

    const extrudeSettings = { depth: height, bevelEnabled: true, bevelThickness: 1, bevelSize: 0.5, bevelSegments: 4 };
    const geo = new THREE.ExtrudeGeometry(shape, extrudeSettings);
    geo.center();
    return geo;
}

function createStarShape(size, height) {
    const shape = new THREE.Shape();
    const points = 5;
    const outerR = size;
    const innerR = size * 0.4;
    for (let i = 0; i < points * 2; i++) {
        const angle = (i * Math.PI) / points - Math.PI / 2;
        const r = i % 2 === 0 ? outerR : innerR;
        if (i === 0) shape.moveTo(r * Math.cos(angle), r * Math.sin(angle));
        else shape.lineTo(r * Math.cos(angle), r * Math.sin(angle));
    }
    shape.closePath();

    const extrudeSettings = { depth: height, bevelEnabled: true, bevelThickness: 0.5, bevelSize: 0.3, bevelSegments: 3 };
    const geo = new THREE.ExtrudeGeometry(shape, extrudeSettings);
    geo.center();
    return geo;
}

function makeTextSprite(text) {
    const canvas = document.createElement('canvas');
    canvas.width = 256;
    canvas.height = 64;
    const ctx = canvas.getContext('2d');
    ctx.fillStyle = 'rgba(0,0,0,0)';
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    ctx.font = '24px sans-serif';
    ctx.fillStyle = '#ffffff';
    ctx.textAlign = 'center';
    ctx.fillText(text, canvas.width / 2, canvas.height / 2 + 8);

    const texture = new THREE.CanvasTexture(canvas);
    const mat = new THREE.SpriteMaterial({ map: texture, transparent: true });
    const sprite = new THREE.Sprite(mat);
    sprite.scale.set(20, 5, 1);
    return sprite;
}

function updatePreview() {
    if (pendingUpdate) {
        cancelAnimationFrame(pendingUpdate);
    }
    pendingUpdate = requestAnimationFrame(() => {
        pendingUpdate = null;
        if (puckGroup) {
            scene.remove(puckGroup);
            puckGroup.traverse((child) => {
                if (child.geometry) child.geometry.dispose();
                if (child.material) {
                    if (child.material.map) child.material.map.dispose();
                    child.material.dispose();
                }
            });
        }
        puckGroup = createPreviewMesh();
        scene.add(puckGroup);
        document.getElementById('preview-status').textContent = 'Preview updated';
    });
}

const sliderConfig = [
    { id: 'base_diameter', valId: 'base_diameter_val', decimals: 0 },
    { id: 'base_thickness', valId: 'base_thickness_val', decimals: 1 },
    { id: 'hole_diameter', valId: 'hole_diameter_val', decimals: 0 },
    { id: 'hole_height', valId: 'hole_height_val', decimals: 1 },
    { id: 'hole_bottom_offset', valId: 'hole_bottom_offset_val', decimals: 1 },
    { id: 'shape_size', valId: 'shape_size_val', decimals: 0 },
    { id: 'shape_height', valId: 'shape_height_val', decimals: 0 },
    { id: 'text_height', valId: 'text_height_val', decimals: 1 },
    { id: 'font_size', valId: 'font_size_val', decimals: 0 },
    { id: 'ai_offset_x', valId: 'ai_offset_x_val', decimals: 1 },
    { id: 'ai_offset_y', valId: 'ai_offset_y_val', decimals: 1 },
    { id: 'ai_offset_z', valId: 'ai_offset_z_val', decimals: 1 },
    { id: 'ai_rotation_x', valId: 'ai_rotation_x_val', decimals: 0 },
    { id: 'ai_rotation_y', valId: 'ai_rotation_y_val', decimals: 0 },
    { id: 'ai_rotation_z', valId: 'ai_rotation_z_val', decimals: 0 },
    { id: 'ai_scale', valId: 'ai_scale_val', decimals: 1 },
    { id: 'upload_offset_x', valId: 'upload_offset_x_val', decimals: 1 },
    { id: 'upload_offset_y', valId: 'upload_offset_y_val', decimals: 1 },
    { id: 'upload_offset_z', valId: 'upload_offset_z_val', decimals: 1 },
    { id: 'upload_rotation_x', valId: 'upload_rotation_x_val', decimals: 0 },
    { id: 'upload_rotation_y', valId: 'upload_rotation_y_val', decimals: 0 },
    { id: 'upload_rotation_z', valId: 'upload_rotation_z_val', decimals: 0 },
    { id: 'upload_scale', valId: 'upload_scale_val', decimals: 1 },
];

function bindControls() {
    for (const cfg of sliderConfig) {
        const el = document.getElementById(cfg.id);
        const val = document.getElementById(cfg.valId);
        el.addEventListener('input', () => {
            val.textContent = parseFloat(el.value).toFixed(cfg.decimals);
            updatePreview();
        });
    }

    document.getElementById('text_content').addEventListener('input', updatePreview);
    document.getElementById('shape_type').addEventListener('change', updatePreview);
    document.getElementById('ai_flip_x').addEventListener('change', updatePreview);
    document.getElementById('ai_flip_y').addEventListener('change', updatePreview);
    document.getElementById('ai_flip_z').addEventListener('change', updatePreview);
    document.getElementById('upload_flip_x').addEventListener('change', updatePreview);
    document.getElementById('upload_flip_y').addEventListener('change', updatePreview);
    document.getElementById('upload_flip_z').addEventListener('change', updatePreview);

    document.getElementById('top_type').addEventListener('change', () => {
        const val = document.getElementById('top_type').value;
        const isAi = val === 'ai_model';
        document.getElementById('shape-options').style.display = val === 'shape' ? '' : 'none';
        document.getElementById('text-options').style.display = val === 'text' ? '' : 'none';
        document.getElementById('upload-options').style.display = val === 'upload' ? '' : 'none';
        document.getElementById('ai-image-options').style.display = isAi ? '' : 'none';
        document.getElementById('btn-generate').style.display = isAi ? 'none' : '';
        document.getElementById('download-links').style.display = 'none';
        if (!isAi) {
            document.getElementById('preview-status').textContent = 'Ready';
        }
        updatePreview();
    });

    document.getElementById('stl_file').addEventListener('change', async (e) => {
        const file = e.target.files[0];
        if (!file) return;

        if (uploadMeshGeo) {
            uploadMeshGeo.dispose();
            uploadMeshGeo = null;
        }
        uploadMeshUrl = null;

        const formData = new FormData();
        formData.append('stl_file', file);
        try {
            const resp = await fetch('/api/upload_stl', { method: 'POST', body: formData });
            const data = await resp.json();
            if (data.upload_path) {
                uploadPath = data.upload_path;
                uploadMeshUrl = data.stl_url;
                document.getElementById('upload-status').textContent = `Loaded: ${file.name}`;
                document.getElementById('upload-status').className = 'upload-status success';

                if (data.stl_url) {
                    const loader = new STLLoader();
                    const geo = await loader.loadAsync(data.stl_url);
                    geo.rotateX(-Math.PI / 2);
                    uploadMeshGeo = geo;
                }
                updatePreview();
            }
        } catch (err) {
            document.getElementById('upload-status').textContent = 'Upload failed';
            document.getElementById('upload-status').className = 'upload-status error';
        }
    });

    document.getElementById('ai_image_file').addEventListener('change', async (e) => {
        const file = e.target.files[0];
        if (!file) return;

        const reader = new FileReader();
        reader.onload = (ev) => {
            aiImageDataUrl = ev.target.result;
            updatePreview();
        };
        reader.readAsDataURL(file);

        const formData = new FormData();
        formData.append('image_file', file);
        try {
            const resp = await fetch('/api/upload_image', { method: 'POST', body: formData });
            const data = await resp.json();
            if (data.upload_path) {
                aiImagePath = data.upload_path;
                document.getElementById('ai-image-status').textContent = `Loaded: ${file.name}`;
                document.getElementById('ai-image-status').className = 'upload-status success';
                document.getElementById('btn-generate-ai').style.display = '';
            }
        } catch (err) {
            document.getElementById('ai-image-status').textContent = 'Upload failed';
            document.getElementById('ai-image-status').className = 'upload-status error';
        }
    });

    document.getElementById('btn-generate').addEventListener('click', generateAndDownload);
    document.getElementById('btn-generate-ai').addEventListener('click', generateAiMeshOnly);
    document.getElementById('btn-download-ai-stl').addEventListener('click', () => exportAiPuck('stl'));
    document.getElementById('btn-download-ai-3mf').addEventListener('click', () => exportAiPuck('3mf'));
}

function showAiProgress(show) {
    const area = document.getElementById('ai-progress-area');
    area.style.display = show ? '' : 'none';
}

function setAiProgress(pct, label) {
    const fill = document.getElementById('ai-progress-fill');
    const lbl = document.getElementById('ai-progress-label');
    fill.style.width = Math.min(pct, 100) + '%';
    if (label) lbl.textContent = label;
}

const AI_PROGRESS_STAGES = [
    { at: 5, label: 'Loading AI models...' },
    { at: 15, label: 'Analyzing image...' },
    { at: 30, label: 'Generating multi-views...' },
    { at: 50, label: 'Reconstructing 3D mesh...' },
    { at: 70, label: 'Refining geometry...' },
    { at: 85, label: 'Making watertight...' },
    { at: 95, label: 'Finalizing...' },
];

function startAiProgressSimulation() {
    let stageIdx = 0;
    let pct = 0;
    const tick = () => {
        if (stageIdx < AI_PROGRESS_STAGES.length && pct >= AI_PROGRESS_STAGES[stageIdx].at) {
            setAiProgress(pct, AI_PROGRESS_STAGES[stageIdx].label);
            stageIdx++;
        }
        setAiProgress(pct, null);
        if (pct < 92) {
            const inc = pct < 30 ? 1.5 : pct < 60 ? 0.8 : 0.3;
            pct = Math.min(pct + inc, 92);
            return setTimeout(tick, 800);
        }
        return null;
    };
    return tick();
}

async function generateAiMeshOnly() {
    if (!aiImagePath) {
        alert('Upload an image first.');
        return;
    }

    const btn = document.getElementById('btn-generate-ai');
    btn.textContent = 'Generating...';
    btn.disabled = true;

    showAiProgress(true);
    setAiProgress(0, 'Starting...');

    const progressCancel = startAiProgressSimulation();

    try {
        const resp = await fetch('/api/generate_ai_mesh', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ai_image_path: aiImagePath }),
        });
        const data = await resp.json();
        if (data.error) {
            setAiProgress(0, 'Error: ' + data.error);
            setTimeout(() => showAiProgress(false), 3000);
            alert('Error: ' + data.error);
            return;
        }

        if (progressCancel) clearTimeout(progressCancel);
        setAiProgress(100, 'Complete!');
        setTimeout(() => showAiProgress(false), 2000);

        aiMeshId = data.mesh_id;
        aiRawStlUrl = data.ai_stl_url;

        const loader = new STLLoader();
        const geo = await loader.loadAsync(data.ai_stl_url);
        geo.rotateX(-Math.PI / 2);
        aiMeshGeo = geo;
        aiMeshMaterial = new THREE.MeshPhysicalMaterial({
            color: 0xe67e22,
            metalness: 0.3,
            roughness: 0.3,
        });
        updatePreview();

        document.getElementById('download-ai-raw-stl').href = data.ai_stl_url;
        document.getElementById('ai-download-links').style.display = 'flex';
        document.getElementById('preview-status').textContent = 'AI mesh generated! Adjust sliders and download.';
    } catch (err) {
        setAiProgress(0, 'Error: ' + err.message);
        setTimeout(() => showAiProgress(false), 3000);
        alert('Error: ' + err.message);
    } finally {
        btn.textContent = 'Generate AI Mesh';
        btn.disabled = false;
    }
}

async function exportAiPuck(format) {
    if (!aiMeshId) {
        alert('Generate the AI mesh first.');
        return;
    }

    const params = {
        ...readFormParams(),
        ai_offset_x: parseFloat(document.getElementById('ai_offset_x').value) || 0,
        ai_offset_y: parseFloat(document.getElementById('ai_offset_y').value) || 0,
        ai_offset_z: parseFloat(document.getElementById('ai_offset_z').value) || 0,
        ai_rotation_x: parseFloat(document.getElementById('ai_rotation_x').value) || 0,
        ai_rotation_y: parseFloat(document.getElementById('ai_rotation_y').value) || 0,
        ai_rotation_z: parseFloat(document.getElementById('ai_rotation_z').value) || 0,
        ai_flip_x: document.getElementById('ai_flip_x').checked,
        ai_flip_y: document.getElementById('ai_flip_y').checked,
        ai_flip_z: document.getElementById('ai_flip_z').checked,
        ai_scale: parseFloat(document.getElementById('ai_scale').value) || 10,
        mesh_id: aiMeshId,
        format: format,
    };

    try {
        const resp = await fetch('/api/export_puck', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(params),
        });
        if (!resp.ok) {
            const err = await resp.json();
            alert('Export failed: ' + (err.error || resp.statusText));
            return;
        }
        const blob = await resp.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `puck.${format}`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        document.getElementById('preview-status').textContent = `Downloaded puck.${format} with current transforms.`;
    } catch (err) {
        alert('Export failed: ' + err.message);
    }
}

async function generateAndDownload() {
    const btn = document.getElementById('btn-generate');
    btn.textContent = 'Generating...';
    btn.disabled = true;

    const params = readFormParams();
    if (params.top_type === 'upload') {
        params.uploaded_stl_path = uploadPath;
    }

    try {
        const resp = await fetch('/api/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(params),
        });
        const data = await resp.json();
        if (data.error) {
            alert('Error: ' + data.error);
            return;
        }

        document.getElementById('download-stl').href = data.stl_url;
        document.getElementById('download-3mf').href = data['3mf_url'];
        document.getElementById('download-links').style.display = 'flex';
        document.getElementById('preview-status').textContent = 'Generation complete!';

        if (data.ai_stl_url) {
            const aiLink = document.getElementById('download-ai-stl') || (() => {
                const a = document.createElement('a');
                a.id = 'download-ai-stl';
                a.className = 'btn btn-secondary';
                a.download = 'ai_model.stl';
                a.textContent = 'Download AI Model Only';
                document.getElementById('download-links').appendChild(a);
                return a;
            })();
            aiLink.href = data.ai_stl_url;
            aiLink.style.display = '';
        }
    } catch (err) {
        alert('Network error: ' + err.message);
    } finally {
        btn.textContent = 'Generate & Download';
        btn.disabled = false;
    }
}

function readFormParams() {
    return {
        base_diameter: parseFloat(document.getElementById('base_diameter').value),
        base_thickness: parseFloat(document.getElementById('base_thickness').value),
        hole_diameter: parseFloat(document.getElementById('hole_diameter').value),
        hole_height: parseFloat(document.getElementById('hole_height').value),
        hole_bottom_offset: parseFloat(document.getElementById('hole_bottom_offset').value),
        top_type: document.getElementById('top_type').value,
        text_content: document.getElementById('text_content').value,
        text_height: parseFloat(document.getElementById('text_height').value),
        font_size: parseInt(document.getElementById('font_size').value),
        shape_type: document.getElementById('shape_type').value,
        shape_params: {
            size: parseFloat(document.getElementById('shape_size').value),
            height: parseFloat(document.getElementById('shape_height').value),
        },
        uploaded_offset_x: parseFloat(document.getElementById('upload_offset_x').value) || 0,
        uploaded_offset_y: parseFloat(document.getElementById('upload_offset_y').value) || 0,
        uploaded_offset_z: parseFloat(document.getElementById('upload_offset_z').value) || 0,
        uploaded_rotation_x: parseFloat(document.getElementById('upload_rotation_x').value) || 0,
        uploaded_rotation_y: parseFloat(document.getElementById('upload_rotation_y').value) || 0,
        uploaded_rotation_z: parseFloat(document.getElementById('upload_rotation_z').value) || 0,
        uploaded_flip_x: document.getElementById('upload_flip_x').checked,
        uploaded_flip_y: document.getElementById('upload_flip_y').checked,
        uploaded_flip_z: document.getElementById('upload_flip_z').checked,
        uploaded_scale: parseFloat(document.getElementById('upload_scale').value) || 1.0,
    };
}

init();

function animate() {
    requestAnimationFrame(animate);
    controls.update();
    renderer.render(scene, camera);
}
animate();

/* ── Tab switching ── */

document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
        btn.classList.add('active');
        document.getElementById('tab-' + btn.dataset.tab).classList.add('active');
        if (btn.dataset.tab === 'puck-designer') {
            onResize();
            updatePreview();
        }
    });
});

/* ── YouTube Downloader ── */

let ytThumbnailPath = null;

document.getElementById('btn-yt-fetch').addEventListener('click', async () => {
    const url = document.getElementById('yt_url').value.trim();
    if (!url) return;

    const btn = document.getElementById('btn-yt-fetch');
    const infoArea = document.getElementById('yt-info-area');
    const errEl = document.getElementById('yt-error');
    errEl.style.display = 'none';
    btn.textContent = 'Fetching...';
    btn.disabled = true;

    try {
        const resp = await fetch('/api/youtube_info', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url }),
        });
        const data = await resp.json();
        if (data.error) {
            errEl.textContent = data.error;
            errEl.style.display = '';
            return;
        }

        document.getElementById('yt-title').textContent = data.title;
        document.getElementById('yt-thumbnail').src = data.thumbnail_path || data.thumbnail_url;
        ytThumbnailPath = data.thumbnail_path;

        const sel = document.getElementById('yt_stream');
        sel.innerHTML = '';
        if (data.streams.length === 0) {
            const opt = document.createElement('option');
            opt.value = '';
            opt.textContent = 'No audio streams found';
            sel.appendChild(opt);
        } else {
            for (const s of data.streams) {
                const opt = document.createElement('option');
                opt.value = s.itag;
                opt.textContent = `${s.abr || 'unknown'} — ${s.mime_type || ''}`;
                sel.appendChild(opt);
            }
        }

        infoArea.style.display = '';
        document.getElementById('yt-download-links').style.display = 'none';
    } catch (err) {
        errEl.textContent = 'Network error: ' + err.message;
        errEl.style.display = '';
    } finally {
        btn.textContent = 'Fetch Video Info';
        btn.disabled = false;
    }
});

document.getElementById('btn-yt-download').addEventListener('click', async () => {
    const url = document.getElementById('yt_url').value.trim();
    if (!url) return;

    const sel = document.getElementById('yt_stream');
    const itag = sel.value;
    if (!itag) {
        alert('No audio stream selected.');
        return;
    }

    const progressArea = document.getElementById('yt-progress-area');
    const progressFill = document.getElementById('yt-progress-fill');
    const progressLabel = document.getElementById('yt-progress-label');
    const links = document.getElementById('yt-download-links');

    const btn = document.getElementById('btn-yt-download');
    btn.textContent = 'Downloading...';
    btn.disabled = true;

    progressArea.style.display = '';
    progressFill.style.width = '0%';
    progressLabel.textContent = 'Downloading...';

    try {
        const resp = await fetch('/api/youtube_download', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url, itag }),
        });
        const data = await resp.json();
        if (data.error) {
            progressLabel.textContent = 'Error: ' + data.error;
            setTimeout(() => { progressArea.style.display = 'none'; }, 3000);
            return;
        }

        progressFill.style.width = '100%';
        progressLabel.textContent = 'Complete!';
        setTimeout(() => { progressArea.style.display = 'none'; }, 2000);

        const audioLink = document.getElementById('yt-download-audio');
        audioLink.href = data.audio_url;
        audioLink.download = data.title + '.mp4';
        links.style.display = '';

        const thumbLink = document.getElementById('yt-download-thumbnail');
        if (data.thumbnail_url) {
            thumbLink.href = data.thumbnail_url;
            thumbLink.style.display = '';
        } else {
            thumbLink.style.display = 'none';
        }
    } catch (err) {
        progressLabel.textContent = 'Error: ' + err.message;
        setTimeout(() => { progressArea.style.display = 'none'; }, 3000);
    } finally {
        btn.textContent = 'Download';
        btn.disabled = false;
    }
});
