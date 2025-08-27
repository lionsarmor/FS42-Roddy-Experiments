const { app, BrowserWindow } = require('electron');
const { exec } = require('child_process');
const path = require('path');
const express = require('express');

function createWindow() {
  const win = new BrowserWindow({
    fullscreen: true,
    frame: false,
    autoHideMenuBar: true,
    webPreferences: {
      contextIsolation: false,
      nodeIntegration: true
    }
  });

  win.loadFile('index.html');
}

app.whenReady().then(() => {
  createWindow();

  // Internal HTTP server for button actions
  const server = express();
  server.get('/launch/:action', (req, res) => {
    const action = req.params.action;
    console.log(`[Kiosk] Launching: ${action}`);

    switch (action) {
      case 'cable':
        exec(`cd ~/mystream-player && npm start >> ~/cable.log 2>&1 &`, {
          detached: true,
          stdio: 'ignore'
        });
        break;

      case 'plex':
        exec('chromium-browser --kiosk --noerrdialogs --disable-infobars --start-fullscreen https://plex.radroddy.com', {
          detached: true,
          stdio: 'ignore'
        });
        break;

      case 'stremio':
        exec('chromium-browser --kiosk --noerrdialogs --disable-infobars --start-fullscreen https://web.strem.io', {
          detached: true,
          stdio: 'ignore'
        });
        break;

      case 'desktop':
      // Disable autologin for next session so lightdm shows login screen
       exec(`sudo sed -i 's/^autologin-user=.*/#autologin-user=/' /etc/lightdm/lightdm.conf && sudo systemctl restart lightdm`, {
          detached: true,
          stdio: 'ignore'
        });
        break;

      case 'shutdown':
        exec('systemctl poweroff', { detached: true, stdio: 'ignore' });
        break;

      case 'reboot':
        exec('systemctl reboot', { detached: true, stdio: 'ignore' });
        break;
    }

    res.sendStatus(200);
  });

  server.listen(8099, () => {
    console.log('Launch server running on http://localhost:8099');
  });
});

app.on('window-all-closed', () => {
  app.quit();
});
