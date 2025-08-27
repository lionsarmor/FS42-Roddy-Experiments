const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('launcher', {
  launchCable: () => ipcRenderer.send('launch-cable'),
  launchPlex: () => ipcRenderer.send('launch-plex'),
  launchStremio: () => ipcRenderer.send('launch-stremio'),
  launchDesktop: () => ipcRenderer.send('launch-desktop'),
  systemCommand: (cmd) => ipcRenderer.send('system-command', cmd)
});
