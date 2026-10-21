// 10.0.2.2 is the Vega Virtual Device's alias for its host. With WSL in mirrored
// networking mode that host loopback is the Windows machine running ChronoGrid.
export const SERVER = 'http://10.0.2.2:8787';
export const WS_URL = SERVER.replace(/^http/, 'ws') + '/ws';
