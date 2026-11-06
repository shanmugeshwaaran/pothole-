document.addEventListener("DOMContentLoaded", () => {
    const mapElement = document.getElementById('customer-map');
    
    if (mapElement) {
        // --- 1. MAP TILE PROVIDERS ---
        const darkMap = L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
            maxZoom: 19, attribution: '© OpenStreetMap, © CARTO'
        });
        const satelliteMap = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
            maxZoom: 19, attribution: 'Tiles © Esri'
        });

        // --- 2. INITIALIZE MAP ---
        const map = L.map('customer-map', {
            center: [13.0827, 80.2707], 
            zoom: 16, 
            layers: [darkMap],
            zoomControl: false 
        });
        
        L.control.zoom({ position: 'bottomright' }).addTo(map);
        L.control.layers({ "Cyber Dark": darkMap, "Satellite View": satelliteMap }).addTo(map);
        
        let markersLayer = L.layerGroup().addTo(map);
        let currentPotholes = []; 
        let userLocation = null; 

        // --- 3. RE-CENTER GPS BUTTON (LOCATE ME) ---
        const recenterBtnControl = L.control({position: 'bottomleft'});
        recenterBtnControl.onAdd = function () {
            let div = L.DomUtil.create('div', 'leaflet-bar leaflet-control');
            div.innerHTML = `
                <button id="recenter-btn" style="background-color: #151b2b; color: #00f0ff; border: 2px solid #00f0ff; padding: 12px; border-radius: 8px; cursor: pointer; font-size: 16px; font-weight: bold; box-shadow: 0 0 15px rgba(0, 240, 255, 0.4);">
                    🎯 Locate Me
                </button>`;
            return div;
        };
        recenterBtnControl.addTo(map);

        document.addEventListener('click', function(e) {
            if (e.target && e.target.id === 'recenter-btn') {
                if (userLocation) {
                    map.flyTo(userLocation, 17, { animate: true, duration: 1.5 }); 
                } else {
                    alert("Still searching for your GPS signal...");
                }
            }
        });

        // --- 4. REAL MOBILE GPS TRACKING ---
        const userIconStyles = `background-color: #3b82f6; width: 18px; height: 18px; display: block; border-radius: 50%; border: 3px solid white;`;
        const userIcon = L.divIcon({
            className: 'custom-pin',
            html: `<span class="pulse-blue" style="${userIconStyles}"></span>`,
            iconSize: [18, 18], iconAnchor: [9, 9]
        });
        
        let userMarker = L.marker([0, 0], {icon: userIcon, zIndexOffset: 1000}); 
        let gpsInitialized = false;

        if ("geolocation" in navigator) {
            navigator.geolocation.watchPosition(
                function(position) {
                    let lat = position.coords.latitude;
                    let lng = position.coords.longitude;
                    userLocation = [lat, lng];

                    if (!gpsInitialized) {
                        userMarker.addTo(map);
                        userMarker.bindPopup("<b style='color:#3b82f6;'>Your Vehicle</b>").openPopup();
                        map.setView(userLocation, 17); // Only auto-center the VERY FIRST time
                        gpsInitialized = true;
                    }

                    userMarker.setLatLng(userLocation); 
                    checkGPSProximity(); 
                },
                function(error) {
                    console.warn("GPS Error:", error);
                },
                { enableHighAccuracy: true, maximumAge: 1000, timeout: 5000 }
            );
        }

        // --- 5. ROUTING MACHINE & SEARCH BAR ---
        let routingControl = L.Routing.control({
            waypoints: [], 
            routeWhileDragging: false,
            showAlternatives: false,
            createMarker: function() { return null; },
            lineOptions: { styles: [{color: '#00f0ff', opacity: 0.8, weight: 5}] }
        }).addTo(map);

        // Allow clicking the map to set destination
        map.on('click', function(e) {
            if (userLocation) {
                let destination = e.latlng;
                let startPoint = L.latLng(userLocation[0], userLocation[1]);
                routingControl.setWaypoints([startPoint, destination]);
            }
        });

        // Search Bar Logic
        const searchBtn = document.getElementById('search-btn');
        const destInput = document.getElementById('destination-input');

        function triggerSearch() {
            const query = destInput.value;
            if (!query) return;
            if (!userLocation) {
                alert("Still searching for your GPS location. Please wait a moment.");
                return;
            }

            searchBtn.innerText = "Searching...";

            fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(query)}`)
                .then(response => response.json())
                .then(data => {
                    searchBtn.innerText = "Navigate"; 
                    if (data && data.length > 0) {
                        let destLat = parseFloat(data[0].lat);
                        let destLon = parseFloat(data[0].lon);
                        let destination = L.latLng(destLat, destLon);
                        let startPoint = L.latLng(userLocation[0], userLocation[1]);
                        
                        routingControl.setWaypoints([startPoint, destination]);
                    } else {
                        alert("Could not find that location. Please try adding the city name.");
                    }
                })
                .catch(err => {
                    console.error("Search error:", err);
                    searchBtn.innerText = "Navigate";
                    alert("Error connecting to search service.");
                });
        }

        if(searchBtn && destInput) {
            searchBtn.addEventListener('click', triggerSearch);
            destInput.addEventListener('keypress', function(e) {
                if (e.key === 'Enter') triggerSearch();
            });
        }

        // --- 6. CHECK DISTANCE TO POTHOLES ---
        function checkGPSProximity() {
            if (currentPotholes.length === 0 || !userLocation) return;
            
            let closestDistance = Infinity;
            let activePotholesNearby = 0;
            let userLatLng = userMarker.getLatLng();

            currentPotholes.forEach(pothole => {
                if (pothole.status === 'FIXED') return; 
                let potholeLatLng = L.latLng(pothole.latitude, pothole.longitude);
                let distance = userLatLng.distanceTo(potholeLatLng); 

                if (distance <= 50) {
                    activePotholesNearby++;
                    if (distance < closestDistance) closestDistance = distance;
                }
            });

            const alertBox = document.getElementById('route-alert');
            const alertMessage = document.getElementById('route-message');

            if (activePotholesNearby > 0) {
                alertBox.classList.remove('hidden', 'safe');
                alertBox.querySelector('h3').innerText = "⚠ PROXIMITY ALERT ⚠";
                alertMessage.innerHTML = `Pothole detected <b>${Math.round(closestDistance)} meters</b> away!<br>Drive carefully!`;
            } else {
                alertBox.classList.add('hidden'); 
            }
        }

        // --- 7. ROUTE WARNING MATH ---
        routingControl.on('routesfound', function(e) {
            let routes = e.routes;
            let routeCoordinates = routes[0].coordinates; 
            let turfLineString = turf.lineString(routeCoordinates.map(c => [c.lng, c.lat]));
            let potholesOnRoute = 0;

            currentPotholes.forEach(pothole => {
                if (pothole.status === 'FIXED') return; 
                let potholePoint = turf.point([pothole.longitude, pothole.latitude]);
                let distance = turf.pointToLineDistance(potholePoint, turfLineString, {units: 'meters'});
                if (distance <= 50) potholesOnRoute++;
            });

            const alertBox = document.getElementById('route-alert');
            const alertMessage = document.getElementById('route-message');
            alertBox.classList.remove('hidden');

            if (potholesOnRoute > 0) {
                alertBox.classList.remove('safe');
                alertBox.querySelector('h3').innerText = "⚠ ROUTE WARNING ⚠";
                alertMessage.innerHTML = `Found <b>${potholesOnRoute}</b> active pothole(s) on your path.`;
            } else {
                alertBox.classList.add('safe');
                alertBox.querySelector('h3').innerText = "CLEAR PATH";
                alertMessage.innerText = "No active potholes detected on this route.";
            }
            setTimeout(() => { alertBox.classList.add('hidden'); }, 7000);
        });

        // --- 8. FETCH AND DISPLAY POTHOLES ---
        function loadLivePotholes() {
            fetch('/api/potholes')
                .then(response => response.json())
                .then(data => {
                    markersLayer.clearLayers(); 
                    currentPotholes = data; 
                    
                    data.forEach(pothole => {
                        let color = '#ef4444'; let pulseClass = 'pulse-red';
                        if (pothole.status === 'REVIEWED') { color = '#f59e0b'; pulseClass = 'pulse-yellow'; }
                        if (pothole.status === 'FIXED') { color = '#10b981'; pulseClass = 'pulse-green'; }

                        const markerStyles = `background-color: ${color}; width: 16px; height: 16px; display: block; border-radius: 50%; border: 2px solid white;`;
                        const customIcon = L.divIcon({
                            className: 'custom-pin', html: `<span class="${pulseClass}" style="${markerStyles}"></span>`,
                            iconSize: [16, 16], iconAnchor: [8, 8], popupAnchor: [0, -10]
                        });

                        let marker = L.marker([pothole.latitude, pothole.longitude], {icon: customIcon});
                        marker.bindPopup(`
                            <div style="font-family:sans-serif;">
                                <h3 style="margin:0 0 5px 0; color:#00f0ff;">Pothole #${pothole.id}</h3>
                                <b style="color:#8892b0;">Status:</b> <span style="color:${color}; font-weight:bold;">${pothole.status}</span>
                            </div>
                        `);
                        markersLayer.addLayer(marker);
                    });
                    checkGPSProximity(); 
                })
                .catch(err => console.error("Error:", err));
        }

        loadLivePotholes(); 
        setInterval(loadLivePotholes, 5000); 
    }
});