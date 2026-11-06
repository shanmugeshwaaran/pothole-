document.addEventListener("DOMContentLoaded", () => {
    const mapElement = document.getElementById('admin-map');
    
    if (mapElement) {
        // --- ADMIN MAP TILE PROVIDERS ---
        // 1. Clean Modern Street Map (Carto Voyager)
        const streetMap = L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
            maxZoom: 19,
            attribution: '© OpenStreetMap, © CARTO'
        });

        // 2. High-Resolution Satellite Map
        const satelliteMap = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
            maxZoom: 19,
            attribution: 'Tiles © Esri'
        });

        // Initialize Map
        const map = L.map('admin-map', {
            center: [13.0827, 80.2707],
            zoom: 13,
            layers: [streetMap]
        });

        // Layer Control Box
        const baseMaps = {
            "Clean Street Map": streetMap,
            "Satellite Imagery": satelliteMap
        };
        L.control.layers(baseMaps).addTo(map);

        // Custom standard Admin Pin (using standard colors)
        function getAdminIcon(status) {
            let color = '#ef4444'; // Red
            if (status === 'REVIEWED') color = '#f59e0b'; // Yellow
            if (status === 'FIXED') color = '#10b981'; // Green

            return L.divIcon({
                className: 'custom-pin',
                html: `<div style="background-color: ${color}; width: 14px; height: 14px; border-radius: 50%; border: 3px solid white; box-shadow: 0 2px 4px rgba(0,0,0,0.5);"></div>`,
                iconSize: [20, 20],
                iconAnchor: [10, 10],
                popupAnchor: [0, -10]
            });
        }

        // Fetch existing potholes
        fetch('/api/potholes')
            .then(response => response.json())
            .then(data => {
                data.forEach(pothole => {
                    let marker = L.marker([pothole.latitude, pothole.longitude], {
                        icon: getAdminIcon(pothole.status)
                    }).addTo(map);
                    
                    let popupContent = `
                        <div style="font-family: sans-serif; color: #1f2937;">
                            <h4 style="margin: 0 0 5px 0; border-bottom: 1px solid #e5e7eb; padding-bottom: 5px;">Record #${pothole.id}</h4>
                            <b>Status:</b> ${pothole.status} <br>
                            <b>Notes:</b> ${pothole.notes || '<i>None</i>'}
                        </div>
                    `;
                    marker.bindPopup(popupContent);
                });
            })
            .catch(err => console.error("Error loading potholes:", err));

        // Click map to add a pothole (Enhanced UI)
        map.on('click', function(e) {
            let lat = e.latlng.lat.toFixed(6);
            let lng = e.latlng.lng.toFixed(6);
            
            let formHtml = `
                <div style="min-width: 220px; font-family: sans-serif; color: #1f2937;">
                    <h4 style="margin-top:0; color:#3b82f6; border-bottom: 2px solid #e5e7eb; padding-bottom: 5px;">Drop Pothole Pin</h4>
                    <form action="/admin/potholes" method="POST" enctype="multipart/form-data">
                        <div style="display: flex; gap: 10px;">
                            <div style="flex:1;">
                                <label style="font-weight:600; font-size:11px; color:#6b7280;">Latitude:</label>
                                <input type="text" name="latitude" value="${lat}" readonly style="width:100%; margin-bottom:8px; padding:6px; border:1px solid #d1d5db; border-radius:4px; background:#f9fafb;">
                            </div>
                            <div style="flex:1;">
                                <label style="font-weight:600; font-size:11px; color:#6b7280;">Longitude:</label>
                                <input type="text" name="longitude" value="${lng}" readonly style="width:100%; margin-bottom:8px; padding:6px; border:1px solid #d1d5db; border-radius:4px; background:#f9fafb;">
                            </div>
                        </div>
                        
                        <label style="font-weight:600; font-size:11px; color:#6b7280;">Status:</label>
                        <select name="status" style="width:100%; margin-bottom:10px; padding:6px; border:1px solid #d1d5db; border-radius:4px;">
                            <option value="DISCOVERED">Discovered (Red)</option>
                            <option value="REVIEWED">Reviewed (Yellow)</option>
                            <option value="FIXED">Fixed (Green)</option>
                        </select>
                        
                        <label style="font-weight:600; font-size:11px; color:#6b7280;">Notes:</label>
                        <input type="text" name="notes" placeholder="Optional details..." style="width:100%; margin-bottom:15px; padding:6px; border:1px solid #d1d5db; border-radius:4px;">
                        
                        <button type="submit" style="background:#3b82f6; color:white; border:none; padding:10px; width:100%; cursor:pointer; border-radius:4px; font-weight:bold; transition: 0.2s;">Save Location</button>
                    </form>
                </div>
            `;
            
            L.popup()
                .setLatLng(e.latlng)
                .setContent(formHtml)
                .openOn(map);
        });
    }
});