import React, { useEffect, useRef, useState } from 'react';
import { Box, Button, ButtonGroup, Typography, Slider, Select, MenuItem } from '@mui/material';
import WaveSurfer from 'wavesurfer.js';
import RegionsPlugin from 'wavesurfer.js/dist/plugins/regions.esm.js';

const AudioPlayer = ({ 
  audioSrc, 
  currentSeek, 
  setCurrentSeek, 
  setIsPlaying, 
  isPlaying,
  fragments,
  stats 
}) => {
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [audioError, setAudioError] = useState(null);
  const [wavesurferReady, setWavesurferReady] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [activeRegion, setActiveRegion] = useState(null);
  const [loopEnabled, setLoopEnabled] = useState(true);
  const [showOperatorRegions, setShowOperatorRegions] = useState(true);
  const [showClientRegions, setShowClientRegions] = useState(true);
  const [showOverlapRegions, setShowOverlapRegions] = useState(true);
  const [volume, setVolume] = useState(1);
  const [playbackRate, setPlaybackRate] = useState(1);
  
  const waveformRef = useRef(null);
  const wavesurferRef = useRef(null);
  const regionsRef = useRef(null);

  const formatTime = (secs) => {
    const minutes = Math.floor(secs / 60);
    const seconds = Math.floor(secs % 60);
    return `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`;
  };

  const clearAllRegions = () => {
    if (regionsRef.current) {
      regionsRef.current.clearRegions();
    }
  };

  const createRegionsFromFragments = () => {
    if (!regionsRef.current || !fragments || fragments.length === 0) return;

    fragments.forEach((frag, index) => {
      if (frag.speaker === 0 && !showOperatorRegions) return;
      if (frag.speaker !== 0 && !showClientRegions) return;

      const startSec = frag.start_ms / 1000;
      const endSec = frag.stop_ms / 1000;
      const speakerLabel = frag.speaker === 0 ? 'Оператор' : 'Клиент';
      const color = frag.speaker === 0 
        ? 'rgba(0, 255, 0, 0.3)'
        : 'rgba(0, 0, 255, 0.3)';

      regionsRef.current.addRegion({
        id: `fragment-${index}`,
        start: startSec,
        end: endSec,
        content: `${speakerLabel}: ${frag.text}`,
        color: color,
        drag: false,
        resize: false,
      });
    });
  };

  const createOverlapRegions = () => {
    if (!regionsRef.current || !stats || !stats.overlapDetails || !stats.overlapDetails.intervals) return;

    stats.overlapDetails.intervals.forEach((interval, index) => {
      const startSec = interval.start_ms / 1000;
      const endSec = interval.end_ms / 1000;

      regionsRef.current.addRegion({
        id: `overlap-${index}`,
        start: startSec,
        end: endSec,
        content: `Наложение: спикеры ${interval.speakers.join(', ')}`,
        color: 'rgba(255, 0, 0, 0.3)',
        drag: false,
        resize: false,
      });
    });
  };

  const handlePlay = () => wavesurferRef.current?.play();
  const handlePause = () => wavesurferRef.current?.pause();
  const handleSkipBackward = () => wavesurferRef.current?.skip(-10);
  const handleSkipForward = () => wavesurferRef.current?.skip(10);
  const toggleLoop = () => setLoopEnabled(!loopEnabled);
  const toggleOperatorRegions = () => setShowOperatorRegions(!showOperatorRegions);
  const toggleClientRegions = () => setShowClientRegions(!showClientRegions);
  const toggleOverlapRegions = () => setShowOverlapRegions(!showOverlapRegions);
  const handleVolumeChange = (e, v) => setVolume(v / 100);
  const handlePlaybackRateChange = (e) => setPlaybackRate(e.target.value);

  useEffect(() => {
    if (!audioSrc || !waveformRef.current) return;

    setIsLoading(true);
    setAudioError(null);
    setWavesurferReady(false);

    const regions = RegionsPlugin.create();
    regionsRef.current = regions;

    wavesurferRef.current = WaveSurfer.create({
      container: waveformRef.current,
      waveColor: '#ddd',
      progressColor: '#764ba2',
      barWidth: 2,
      height: 60,
      normalize: true,
      backend: 'MediaElement',
      interact: true,
      url: audioSrc,
      plugins: [regions],
    });

    wavesurferRef.current.on('ready', () => {
      setDuration(wavesurferRef.current.getDuration());
      setWavesurferReady(true);
      setIsLoading(false);
    });

    wavesurferRef.current.on('play', () => setIsPlaying(true));
    wavesurferRef.current.on('pause', () => setIsPlaying(false));
    wavesurferRef.current.on('finish', () => {
      setIsPlaying(false);
      setCurrentSeek({ start: null, stop: null });
    });

    wavesurferRef.current.on('audioprocess', () => {
      const current = wavesurferRef.current.getCurrentTime();
      setCurrentTime(current);
      if (currentSeek.stop !== null && current >= currentSeek.stop) {
        wavesurferRef.current.pause();
        setIsPlaying(false);
        setCurrentSeek({ start: null, stop: null });
      }
    });

    regions.on('region-clicked', (region, e) => {
      e.stopPropagation();
      setActiveRegion(region);
      region.play();
      setCurrentSeek({ start: region.start, stop: region.end });
    });

    regions.on('region-in', (region) => setActiveRegion(region));
    regions.on('region-out', (region) => {
      if (activeRegion === region && loopEnabled) {
        region.play();
      } else if (activeRegion === region) {
        setActiveRegion(null);
      }
    });

    wavesurferRef.current.on('interaction', () => setActiveRegion(null));

    wavesurferRef.current.on('error', (err) => {
      console.error('WaveSurfer error:', err);
      setAudioError('Ошибка: ' + (err.message || err));
      setIsLoading(false);
    });

    return () => {
      if (wavesurferRef.current) {
        try {
          wavesurferRef.current.destroy();
        } catch (err) {
          console.warn('Destroy ignored:', err);
        }
        wavesurferRef.current = null;
        regionsRef.current = null;
      }
      setWavesurferReady(false);
      setIsPlaying(false);
      setCurrentTime(0);
      setDuration(0);
      setIsLoading(false);
      setActiveRegion(null);
    };
  }, [audioSrc, fragments, stats, setIsPlaying, setCurrentSeek, currentSeek.stop]);

  useEffect(() => {
    if (wavesurferReady && regionsRef.current) {
      clearAllRegions();
      createRegionsFromFragments();
      if (showOverlapRegions) createOverlapRegions();
    }
  }, [wavesurferReady, showOperatorRegions, showClientRegions, showOverlapRegions, fragments, stats]);

  useEffect(() => {
    if (wavesurferRef.current && wavesurferReady) {
      wavesurferRef.current.setVolume(volume);
    }
  }, [volume, wavesurferReady]);

  useEffect(() => {
    if (wavesurferRef.current && wavesurferReady) {
      wavesurferRef.current.setPlaybackRate(playbackRate);
    }
  }, [playbackRate, wavesurferReady]);

  useEffect(() => {
    if (wavesurferRef.current && wavesurferReady && duration > 0 && currentSeek.start !== null) {
      wavesurferRef.current.seekTo(currentSeek.start / duration);
      wavesurferRef.current.play().catch(() => console.warn('Play blocked'));
    }
  }, [currentSeek, duration, wavesurferReady]);

  if (audioError) return <Typography color="error">{audioError}</Typography>;
  if (!audioSrc) return <Typography color="warning">Загрузка аудио...</Typography>;

  return (
    <>
      <div ref={waveformRef} style={{ width: '100%', minHeight: '60px', background: '#fff' }} />
      {wavesurferReady ? (
        <Box sx={{ display: 'flex', alignItems: 'center', mt: 1, flexWrap: 'wrap', gap: 1 }}>
          <ButtonGroup size="small">
            <Button onClick={handleSkipBackward}>-10с</Button>
            <Button onClick={handlePlay} disabled={isPlaying}>Старт</Button>
            <Button onClick={handlePause} disabled={!isPlaying}>Стоп</Button>
            <Button onClick={handleSkipForward}>+10с</Button>
            <Button onClick={toggleOperatorRegions} variant={showOperatorRegions ? 'contained' : 'outlined'} size="small">
              Оператор: {showOperatorRegions ? 'Вкл' : 'Выкл'}
            </Button>
            <Button onClick={toggleClientRegions} variant={showClientRegions ? 'contained' : 'outlined'} size="small">
              Клиент: {showClientRegions ? 'Вкл' : 'Выкл'}
            </Button>
            <Button onClick={toggleOverlapRegions} variant={showOverlapRegions ? 'contained' : 'outlined'} size="small">
              Наложения: {showOverlapRegions ? 'Вкл' : 'Выкл'}
            </Button>
          </ButtonGroup>
          <Box sx={{ width: 100, mx: 1 }}>
            <Slider value={volume * 100} onChange={handleVolumeChange} min={0} max={100} size="small" />
          </Box>
          <Select value={playbackRate} onChange={handlePlaybackRateChange} size="small" sx={{ minWidth: 80 }}>
            <MenuItem value={0.5}>0.5x</MenuItem>
            <MenuItem value={1}>1x</MenuItem>
            <MenuItem value={1.5}>1.5x</MenuItem>
            <MenuItem value={2}>2x</MenuItem>
          </Select>
          <Typography variant="body2">{formatTime(currentTime)} / {formatTime(duration)}</Typography>
          {activeRegion && <Typography variant="caption" color="primary">Актив: {activeRegion.content.textContent}</Typography>}
        </Box>
      ) : (
        <Typography color="warning" sx={{ mt: 1 }}>Обработка аудио...</Typography>
      )}
    </>
  );
};

export default AudioPlayer;