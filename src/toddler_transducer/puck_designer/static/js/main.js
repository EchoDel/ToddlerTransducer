import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { TextGeometry } from 'three/addons/geometries/TextGeometry.js';
import { FontLoader } from 'three/addons/loaders/FontLoader.js';

let scene, camera, renderer, controls;
let puckGroup = null;
let font = null;
let pendingUpdate = null;
let uploadPath = null;

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
    } else if (topType === 'upload' && uploadPath) {
        const placeholder = new THREE.Mesh(
            new THREE.BoxGeometry(20, 10, 20),
            new THREE.MeshPhysicalMaterial({
                color: 0x2ecc71,
                metalness: 0.1,
                roughness: 0.6,
                transparent: true,
                opacity: 0.5,
            })
        );
        placeholder.position.y = halfThick + 5;
        group.add(placeholder);

        const labelSprite = makeTextSprite('STL loaded');
        labelSprite.position.y = halfThick + 15;
        group.add(labelSprite);
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

    document.getElementById('top_type').addEventListener('change', () => {
        const val = document.getElementById('top_type').value;
        document.getElementById('shape-options').style.display = val === 'shape' ? '' : 'none';
        document.getElementById('text-options').style.display = val === 'text' ? '' : 'none';
        document.getElementById('upload-options').style.display = val === 'upload' ? '' : 'none';
        updatePreview();
    });

    document.getElementById('stl_file').addEventListener('change', async (e) => {
        const file = e.target.files[0];
        if (!file) return;
        const formData = new FormData();
        formData.append('stl_file', file);
        try {
            const resp = await fetch('/api/upload_stl', { method: 'POST', body: formData });
            const data = await resp.json();
            if (data.upload_path) {
                uploadPath = data.upload_path;
                document.getElementById('upload-status').textContent = `Loaded: ${file.name}`;
                document.getElementById('upload-status').className = 'upload-status success';
                updatePreview();
            }
        } catch (err) {
            document.getElementById('upload-status').textContent = 'Upload failed';
            document.getElementById('upload-status').className = 'upload-status error';
        }
    });

    document.getElementById('btn-generate').addEventListener('click', generateAndDownload);
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
    };
}

init();

function animate() {
    requestAnimationFrame(animate);
    controls.update();
    renderer.render(scene, camera);
}
animate();
