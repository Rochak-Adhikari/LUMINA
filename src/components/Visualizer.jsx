import React, { useEffect, useRef } from 'react';
import * as THREE from 'three';

const Visualizer = ({ audioData, isListening, intensity = 0, width = 600, height = 400 }) => {
    const containerRef = useRef(null);
    const intensityRef = useRef(intensity);
    const isListeningRef = useRef(isListening);

    useEffect(() => {
        intensityRef.current = intensity;
        isListeningRef.current = isListening;
    }, [intensity, isListening]);

    useEffect(() => {
        const container = containerRef.current;
        if (!container) return;

        const w = width;
        const h = height;

        // Scene, Camera, Renderer
        const scene = new THREE.Scene();
        const camera = new THREE.PerspectiveCamera(75, w / h, 0.1, 1000);
        camera.position.z = 4.2;

        const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
        renderer.setSize(w, h);
        renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
        container.appendChild(renderer.domElement);

        // Styling colors matching design system (a8e8ff and 89f2ff)
        const primaryColor = new THREE.Color(0x00D4FF);
        const secondaryColor = new THREE.Color(0x68F0FF);

        // Core Orb Mesh
        const coreGeometry = new THREE.SphereGeometry(1.0, 64, 64);
        const coreMaterial = new THREE.MeshPhongMaterial({
            color: primaryColor,
            emissive: primaryColor,
            emissiveIntensity: 0.6,
            transparent: true,
            opacity: 0.85,
            shininess: 120,
        });
        const core = new THREE.Mesh(coreGeometry, coreMaterial);
        scene.add(core);

        // Inner Glow / Secondary energy envelope
        const innerGeometry = new THREE.SphereGeometry(1.2, 32, 32);
        const innerMaterial = new THREE.MeshStandardMaterial({
            color: secondaryColor,
            transparent: true,
            opacity: 0.18,
            wireframe: false,
        });
        const innerOrb = new THREE.Mesh(innerGeometry, innerMaterial);
        scene.add(innerOrb);

        // Torus Rings Group
        const ringGroup = new THREE.Group();
        scene.add(ringGroup);

        const createRing = (radius, tiltX, tiltY, speed) => {
            const geometry = new THREE.TorusGeometry(radius, 0.015, 16, 100);
            const material = new THREE.MeshBasicMaterial({
                color: primaryColor,
                transparent: true,
                opacity: 0.35,
            });
            const ring = new THREE.Mesh(geometry, material);
            ring.rotation.x = tiltX;
            ring.rotation.y = tiltY;
            ring.userData = { speed };
            ringGroup.add(ring);
            return ring;
        };

        const rings = [
            createRing(1.5, Math.PI / 4, Math.PI / 6, 0.006),
            createRing(1.7, -Math.PI / 3, Math.PI / 4, -0.004),
            createRing(1.9, Math.PI / 2.5, -Math.PI / 5, 0.008),
        ];

        // Particles System
        const particlesCount = 140;
        const particlesGeometry = new THREE.BufferGeometry();
        const posArray = new Float32Array(particlesCount * 3);

        for (let i = 0; i < particlesCount * 3; i++) {
            posArray[i] = (Math.random() - 0.5) * 5.5;
        }
        particlesGeometry.setAttribute('position', new THREE.BufferAttribute(posArray, 3));

        const particlesMaterial = new THREE.PointsMaterial({
            size: 0.025,
            color: secondaryColor,
            transparent: true,
            opacity: 0.65,
            blending: THREE.AdditiveBlending,
        });

        const particleMesh = new THREE.Points(particlesGeometry, particlesMaterial);
        scene.add(particleMesh);

        // Lights
        const ambientLight = new THREE.AmbientLight(0xffffff, 0.25);
        scene.add(ambientLight);

        const pointLight = new THREE.PointLight(primaryColor, 2.5, 12);
        pointLight.position.set(2, 2.5, 2);
        scene.add(pointLight);

        let animationFrameId;

        // Render loop
        const animate = () => {
            animationFrameId = requestAnimationFrame(animate);
            const time = Date.now() * 0.001;

            const currentIntensity = intensityRef.current;
            const currentIsListening = isListeningRef.current;

            // Base breathing scale + audio intensity multiplier
            const baseScale = 1.0 + Math.sin(time * 1.5) * 0.03;
            const targetScale = baseScale + (currentIntensity * 0.45);

            core.scale.set(targetScale, targetScale, targetScale);
            innerOrb.scale.set(targetScale * 1.15, targetScale * 1.15, targetScale * 1.15);

            // Change glowing colors based on state
            if (currentIsListening) {
                // Listening: cyan
                coreMaterial.color.setHex(0x00D4FF);
                coreMaterial.emissive.setHex(0x00D4FF);
                coreMaterial.emissiveIntensity = 0.6 + (currentIntensity * 0.4);
            } else {
                // Speaking / Output state: violet
                coreMaterial.color.setHex(0x8B5CF6);
                coreMaterial.emissive.setHex(0x8B5CF6);
                coreMaterial.emissiveIntensity = 0.55 + (currentIntensity * 0.55);
            }

            // Animate rings rotation based on speed and intensity
            ringGroup.children.forEach((ring) => {
                const speedMultiplier = 1.0 + (currentIntensity * 5.0);
                ring.rotation.z += ring.userData.speed * speedMultiplier;
                ring.scale.set(1.0 + currentIntensity * 0.2, 1.0 + currentIntensity * 0.2, 1.0);
            });

            // Particles drift animation
            particleMesh.rotation.y += 0.0008;
            particleMesh.rotation.x += 0.0004;

            renderer.render(scene, camera);
        };

        animate();

        // Cleanup
        return () => {
            cancelAnimationFrame(animationFrameId);
            renderer.dispose();
            if (container.contains(renderer.domElement)) {
                container.removeChild(renderer.domElement);
            }
        };
    }, [width, height]);

    return (
        <div className="relative flex items-center justify-center" style={{ width, height }}>
            {/* Ambient Background Glow of Orb */}
            <div className="absolute w-[240px] h-[240px] rounded-full bg-primary/10 blur-[80px] pointer-events-none -z-10 animate-pulse" />
            
            {/* Container for Three.js WebGL canvas */}
            <div ref={containerRef} className="absolute inset-0 w-full h-full pointer-events-none" />

            {/* Glowing LUNA text overlay in center */}
            <div className="absolute inset-0 flex items-center justify-center pointer-events-none z-10">
                <div
                    className="text-cyan-100 font-bold tracking-[0.25em] drop-shadow-[0_0_15px_rgba(6,182,212,0.4)] animate-pulse uppercase select-none font-sora"
                    style={{ fontSize: Math.min(width, height) * 0.08 }}
                >
                    Luna
                </div>
            </div>
        </div>
    );
};

export default Visualizer;
