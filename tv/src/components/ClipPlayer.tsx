import React, {useEffect, useRef} from 'react';
import {StyleSheet} from 'react-native';
import {KeplerVideoSurfaceView, VideoPlayer} from '@amazon-devices/react-native-w3cmedia';
import {SERVER} from '../config';

/** Clips stored locally are addressed via the server's own host, which the TV reaches differently. */
function reachable(url: string): string {
  return url.replace(/^https?:\/\/(127\.0\.0\.1|localhost|0\.0\.0\.0)(:\d+)?/, SERVER);
}

// The VVD can't create a new playback session while the previous player is still tearing down.
let lastTeardown: Promise<unknown> = Promise.resolve();

/** Loops a short H.264 clip, muted, on a native video surface. */
export const ClipPlayer = ({
  url,
  onError,
  onSize,
}: {
  url: string;
  onError: () => void;
  onSize: (width: number, height: number) => void;
}) => {
  const player = useRef<VideoPlayer | null>(null);
  const surface = useRef<string | null>(null);
  const ready = useRef(false);

  useEffect(() => {
    let alive = true;
    let p: VideoPlayer | null = null;
    let sizer: ReturnType<typeof setInterval> | undefined;
    ready.current = false;
    const started = lastTeardown
      .then(async () => {
        if (!alive) {
          return;
        }
        const vp = new VideoPlayer();
        p = vp;
        player.current = vp;
        await vp.initialize();
        if (!alive) {
          return;
        }
        // the VVD doesn't reliably fire loadedmetadata, so poll for the decoded size instead
        let polls = 0;
        const timer = setInterval(() => {
          if (vp.videoWidth && vp.videoHeight) {
            clearInterval(timer);
            if (alive) {
              onSize(vp.videoWidth, vp.videoHeight);
            }
          } else if (++polls > 60) {
            clearInterval(timer);
          }
        }, 250);
        sizer = timer;
        vp.loop = true;
        vp.muted = true;
        vp.addEventListener('error', () => alive && onError());
        vp.src = reachable(url);
        ready.current = true;
        if (surface.current) {
          vp.setSurfaceHandle(surface.current);
          vp.play().catch(onError);
        }
      })
      .catch(() => alive && onError());
    return () => {
      alive = false;
      if (sizer) {
        clearInterval(sizer);
      }
      const handle = surface.current;
      player.current = null;
      lastTeardown = started
        .then(async () => {
          if (!p) {
            return;
          }
          p.pause();
          if (handle) {
            p.clearSurfaceHandle(handle);
          }
          await p.deinitialize();
        })
        .catch(() => undefined);
    };
  }, [url, onError, onSize]);

  return (
    <KeplerVideoSurfaceView
      style={StyleSheet.absoluteFill}
      scalingmode="fit"
      onSurfaceViewCreated={(handle: string) => {
        surface.current = handle;
        if (player.current && ready.current) {
          player.current.setSurfaceHandle(handle);
          player.current.play().catch(onError);
        }
      }}
      onSurfaceViewDestroyed={(handle: string) => {
        player.current?.clearSurfaceHandle(handle);
        surface.current = null;
      }}
    />
  );
};
