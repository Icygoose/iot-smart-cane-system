let sidebarOpen = false;
const sidebar = document.getElementById('sidebar');

function openSidebar() {

  if (!sidebarOpen) {
    sidebar.classList.add('sidebar-responsive');
    sidebarOpen = true;
  }
}

function closeSidebar() {
  if (sidebarOpen) {
    sidebar.classList.remove('sidebar-responsive');
    sidebarOpen = false;
  }
}

// Socket.IO Connection
let socket = null; 
let isObstacleDetectionOn = false; 
let isFallingDetectionOn = false;  
let isGPSOn = false;
let isLightingOn = false; 
let locationHistory = [];
let lastFallData = null;

window.addEventListener('load', () => {
  // Connect to Socket.IO server
  socket = io.connect('http://172.20.10.3:5000');

  socket.on('connect', () => {
    console.log('Socket.IO connected successfully');
  });

  socket.on('disconnect', () => {
    console.log('Socket.IO disconnected');
  });

  socket.on('obstacle_update', (data) => {
    const midElem = document.getElementById('middle-distance'); 
    const bottomElem = document.getElementById('bottom-distance'); 
    const obstacleStatusElem = document.getElementById('obstacleDetected-status');

    if (data.middle_distance) {
      midElem.textContent = `${data.middle_distance} cm`;
    }

    if (data.bottom_distance) {
      bottomElem.textContent = `${data.bottom_distance} cm`;
    }

    if (data.obstacleDetected_status === 'obstacle_detected') {
      obstacleStatusElem.textContent = 'Obstacle Detected!';
      obstacleStatusElem.classList.add('status-alert');
    } else {
      obstacleStatusElem.textContent = 'Safe';
      obstacleStatusElem.classList.remove('status-alert'); 
    }
  });

  socket.on('falling_update', (data) => {
    const accElem = document.getElementById('acceleration');
    const gyroElem = document.getElementById('gyroscope');
    const fallStatusElem = document.getElementById('fall-status');

    if (data.acceleration && 
        typeof data.acceleration.x === 'number' &&
        typeof data.acceleration.y === 'number' &&
        typeof data.acceleration.z === 'number') {
        accElem.textContent = `X=${data.acceleration.x.toFixed(2)} m/s², Y=${data.acceleration.y.toFixed(2)} m/s², Z=${data.acceleration.z.toFixed(2)} m/s²`;
    } else {
        accElem.textContent = 'Data not available';
    }

    if (data.gyroscope && 
        typeof data.gyroscope.x === 'number' &&
        typeof data.gyroscope.y === 'number' &&
        typeof data.gyroscope.z === 'number') {
        gyroElem.textContent = `X=${data.gyroscope.x.toFixed(2)} °/s, Y=${data.gyroscope.y.toFixed(2)} °/s, Z=${data.gyroscope.z.toFixed(2)} °/s`;
    } else {
        gyroElem.textContent = 'Data not available';
    }

    if (data.fall_status === 'fall_detected') {
      fallStatusElem.textContent = 'Fall Detected!';
      fallStatusElem.classList.add('status-alert'); 
    } else {
      fallStatusElem.textContent = 'Safe';
      fallStatusElem.classList.remove('status-alert');  
    }
  });

  socket.on('gps_update', (data) => {
    const locationElem = document.getElementById('location');
    const timeElem = document.getElementById('location-time');
    const historyElem = document.getElementById('location-history');

    const latitude = data.latitude;
    const longitude = data.longitude;
    const timestamp = data.timestamp;

    locationElem.textContent = `Latitude: ${latitude}, Longitude: ${longitude}`;
    timeElem.textContent = timestamp;

    // Update location history
    locationHistory.push({ latitude, longitude, timestamp });

    // Keep only the last 10 entries
    if (locationHistory.length > 10) {
      locationHistory.shift();
    }

    // Update the history display
    historyElem.innerHTML = '';
    locationHistory.forEach(loc => {
      const listItem = document.createElement('li');
      listItem.textContent = `${loc.timestamp} - Lat: ${loc.latitude}, Lon: ${loc.longitude}`;
      historyElem.appendChild(listItem);
    });
  });

  socket.on('lighting_update', (data) => {
    const lightingStatusElem = document.getElementById('lighting-status');
    const lightingToggleIcon = document.querySelector('.lighting-toggle');
    
    isLightingOn = data.lighting_status === 'on'; 
    lightingStatusElem.textContent = isLightingOn ? 'On' : 'Off';
    
    if (isLightingOn) {
      lightingToggleIcon.classList.add("lighting-on");
    } else {
      lightingToggleIcon.classList.remove("lighting-on");
    }
  });

  socket.on('fall_alert_sent', function(data) {
    lastFallData = data.fallData;
    document.getElementById('fall-alert-message').textContent = data.message;
    document.getElementById('fallAlertModal').style.display = 'block';
  });

  // Chart rendering
  
  // Obstacle detection per hour
  var optionsObstacle = {
    chart: {
      type: 'line'
    },
    series: [{
      name: 'Obstacles Detected',
      data: obstacleCountsPerHour
    }],
    xaxis: {
      categories: [...Array(24).keys()].map(i => `${i}:00`)
    },
    yaxis: {
      title: {
        text: 'Obstacle Count'
      }
    },
    title: {
      text: 'Obstacles Detected Per Hour in Last 24 Hours',
      align: 'left'
    }
  };

  var chartObstacle = new ApexCharts(document.querySelector("#obstacle-chart"), optionsObstacle);
  chartObstacle.render();

  // Fall detection per hour
  var optionsFallPerHour = {
    chart: {
      type: 'line'
    },
    series: [{
      name: 'Falls Detected',
      data: fallCountsPerHour
    }],
    xaxis: {
      categories: [...Array(24).keys()].map(i => `${i}:00`)
    },
    yaxis: {
      title: {
        text: 'Fall Count'
      }
    },
    title: {
      text: 'Falls Detected Per Hour in Last 24 Hours',
      align: 'left'
    }
  };

  var chartFallPerHour = new ApexCharts(document.querySelector("#fall-per-hour-chart"), optionsFallPerHour);
  chartFallPerHour.render();

  // Fall detection per day
  var fallCounts = fallsPerDay.map(item => item.count).reverse();
  var fallDates = fallsPerDay.map(item => item.date).reverse();

  var optionsFalls = {
    chart: {
      type: 'bar'
    },
    series: [{
      name: 'Falls',
      data: fallCounts
    }],
    xaxis: {
      categories: fallDates
    },
    yaxis: {
      title: {
        text: 'Number of Falls'
      }
    },
    title: {
      text: 'Falls Per Day in Last 7 Days',
      align: 'left'
    }
  };

  var chartFalls = new ApexCharts(document.querySelector("#falls-chart"), optionsFalls);
  chartFalls.render();

  // Top locations by time spent
  var locationLabels = topLocations.map((loc) => {
    let lat = loc.lat.toFixed(2);
    let lon = loc.lon.toFixed(2);
    return `Lat: ${lat}, Lon: ${lon}`;
  });

  var timeSpent = topLocations.map(loc => parseFloat((loc.time_spent / 60).toFixed(2))); // Convert to minutes and keep two decimal places

  var optionsTopLocations = {
    chart: {
      type: 'bar',
      toolbar: {
        show: false
      }
    },
    series: [{
      name: 'Time Spent (minutes)',
      data: timeSpent
    }],
    xaxis: {
      categories: locationLabels,
      labels: {
        rotate: -45,
        style: {
          fontSize: '12px'
        }
      }
    },
    yaxis: {
      title: {
        text: 'Time Spent (minutes)'
      }
    },
    title: {
      text: 'Top 5 Locations by Time Spent',
      align: 'left'
    },
    tooltip: {
      y: {
        formatter: function (val) {
          return val + " minutes";
        }
      }
    }
  };

  var chartTopLocations = new ApexCharts(document.querySelector("#top-locations-chart"), optionsTopLocations);
  chartTopLocations.render();


});

// -------------------- Obstacle Detection Function --------------------
function toggleObstacle() {
  const obstacleStatus = document.getElementById('obstacle-status');
  const obstacleToggleIcon = document.querySelector('.obstacle-toggle');

  if (socket) {
    if (isObstacleDetectionOn) {
      obstacleStatus.textContent = 'Off';
      obstacleToggleIcon.classList.remove("obstacle-on");
      isObstacleDetectionOn = false;

      document.getElementById('middle-distance').textContent = 'N/A';
      document.getElementById('bottom-distance').textContent = 'N/A';
      document.getElementById('obstacleDetected-status').textContent = 'Safe';

      socket.emit('toggle_obstacle_detection', 'off');
    } else {
      obstacleStatus.textContent = 'On';
      obstacleToggleIcon.classList.add("obstacle-on");
      isObstacleDetectionOn = true;

      socket.emit('toggle_obstacle_detection', 'on');
    }
  } else {
    console.error('Socket.IO connection not established');
  }
}

// -------------------- Falling Detection Function --------------------
function toggleFalling() {
  const fallingStatus = document.getElementById('falling-status');
  const fallingToggleIcon = document.querySelector('.falling-toggle');

  if (socket) {
    if (isFallingDetectionOn) {
      fallingStatus.textContent = 'Off';
      fallingToggleIcon.classList.remove("falling-on");
      isFallingDetectionOn = false;

      document.getElementById('acceleration').textContent = 'N/A';
      document.getElementById('gyroscope').textContent = 'N/A';
      document.getElementById('fall-status').textContent = 'Safe';

      socket.emit('toggle_fall_detection', 'off');
    } else {
      fallingStatus.textContent = 'On';
      fallingToggleIcon.classList.add("falling-on");
      isFallingDetectionOn = true;

      socket.emit('toggle_fall_detection', 'on');
    }
  } else {
    console.error('Socket.IO connection not established');
  }
}

// -------------------- GPS Tracking Function --------------------
function toggleLocation() {
  const locationStatusElem = document.getElementById('location-status');
  const locationToggleIcon = document.querySelector('.location-toggle');

  if (socket) {
    const newStatus = isGPSOn ? 'off' : 'on';
    socket.emit('toggle_gps_tracking', newStatus);

    isGPSOn = !isGPSOn;
    locationStatusElem.textContent = isGPSOn ? 'On' : 'Off';
    locationToggleIcon.classList.toggle("location-on", isGPSOn);

    if (!isGPSOn) {
      document.getElementById('location').textContent = 'N/A';
      document.getElementById('location-time').textContent = 'N/A';
      document.getElementById('location-history').innerHTML = '';
      locationHistory = [];
    }
  } else {
    console.error('Socket.IO connection not established');
  }
}


// -------------------- Lighting Function --------------------

function toggleLighting() {
  const lightingStatusElem = document.getElementById('lighting-status');
  const lightingToggleIcon = document.querySelector('.lighting-toggle');

  if (socket) {
    const newStatus = isLightingOn ? 'off' : 'on';  
    socket.emit('toggle_lighting', newStatus); 

    lightingStatusElem.textContent = newStatus === 'on' ? 'On' : 'Off';
    if (newStatus === 'on') {
      lightingToggleIcon.classList.add("lighting-on");
    } else {
      lightingToggleIcon.classList.remove("lighting-on");
    }

    isLightingOn = !isLightingOn;
  } else {
    console.error('Socket.IO connection not established');
  }
}

// -------------------- Alert --------------------
// Close the fall alert modal
function closeFallAlertModal() {
  document.getElementById('fallAlertModal').style.display = 'none';
}

// Open the map to the last fall location
function openFallingLocation() {
  if (
    lastFallData &&
    lastFallData.gps &&
    lastFallData.gps.latitude !== undefined &&
    lastFallData.gps.longitude !== undefined &&
    lastFallData.gps.latitude !== null &&
    lastFallData.gps.longitude !== null
  ) {
      const latitude = lastFallData.gps.latitude;
      const longitude = lastFallData.gps.longitude;
      const mapUrl = `https://www.google.com/maps/search/?api=1&query=${latitude},${longitude}`;
      window.open(mapUrl, '_blank');
  } else {
      alert('GPS data is not available.');
  }
}





