"""Render all frames in parallel and pipe them into ffmpeg together with the soundtrack."""
import os, sys, subprocess, time
from multiprocessing import Pool
import imageio_ffmpeg
from core import W, H, FPS, NF


def work(i):
    import scene
    s = scene.render(i / FPS)
    return bytes(s.get_data())


if __name__ == '__main__':
    out = sys.argv[1]
    audio = sys.argv[2]
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    cmd = [ff, '-y', '-loglevel', 'error',
           '-f', 'rawvideo', '-pix_fmt', 'bgra', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
           '-i', audio,
           '-c:v', 'libx264', '-preset', 'slow', '-crf', '18', '-maxrate', '10500k', '-bufsize', '21000k', '-pix_fmt', 'yuv420p', '-profile:v', 'high',
           '-level', '4.2', '-r', str(FPS), '-g', str(FPS * 2),
           '-c:a', 'aac', '-b:a', '192k', '-ar', '48000',
           '-color_primaries', 'bt709', '-color_trc', 'bt709', '-colorspace', 'bt709',
           '-movflags', '+faststart', '-shortest', out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    t0 = time.time()
    with Pool(4) as pool:
        for i, data in enumerate(pool.imap(work, range(NF), chunksize=2)):
            p.stdin.write(data)
            if i % 60 == 0:
                print(f'frame {i}/{NF}  {time.time() - t0:.0f}s', flush=True)
    p.stdin.close()
    p.wait()
    print('done', p.returncode, f'{time.time() - t0:.0f}s')
