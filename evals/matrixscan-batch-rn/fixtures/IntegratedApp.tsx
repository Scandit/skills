// A working MatrixScan Batch integration. BarcodeBatch is wired with a
// BarcodeBatchBasicOverlay in Frame style, camera lifecycle is managed via useEffect,
// and the listener is attached via addListener.
// Use this fixture for tests that modify or extend an existing integration.

import React, { useEffect, useRef } from 'react';
import { AppState, AppStateStatus } from 'react-native';
import {
  BarcodeBatch,
  BarcodeBatchBasicOverlay,
  BarcodeBatchBasicOverlayStyle,
  BarcodeBatchSession,
  BarcodeBatchSettings,
  Symbology,
  TrackedBarcode,
} from 'scandit-react-native-datacapture-barcode';
import {
  Brush,
  Camera,
  Color,
  DataCaptureView,
  FrameSourceState,
} from 'scandit-react-native-datacapture-core';
import { DataCaptureContext } from 'scandit-react-native-datacapture-core';

DataCaptureContext.initialize('-- ENTER YOUR SCANDIT LICENSE KEY HERE --');
const dataCaptureContext = DataCaptureContext.sharedInstance;

export const ScanScreen = () => {
  const viewRef = useRef<DataCaptureView>(null);
  const cameraRef = useRef<Camera | null>(null);

  const barcodeBatchRef = useRef<BarcodeBatch>(null!);
  if (!barcodeBatchRef.current) {
    const settings = new BarcodeBatchSettings();
    settings.enableSymbologies([
      Symbology.EAN13UPCA,
      Symbology.EAN8,
      Symbology.Code128,
    ]);

    const batch = new BarcodeBatch(settings);
    batch.addListener({
      didUpdateSession: async (_batch: BarcodeBatch, session: BarcodeBatchSession) => {
        Object.values(session.trackedBarcodes).forEach((tracked: TrackedBarcode) => {
          console.log('Tracking:', tracked.barcode.data);
        });
      },
    });

    dataCaptureContext.setMode(batch);
    barcodeBatchRef.current = batch;
  }

  const overlayRef = useRef<BarcodeBatchBasicOverlay>(null!);
  if (!overlayRef.current) {
    overlayRef.current = new BarcodeBatchBasicOverlay(
      barcodeBatchRef.current,
      BarcodeBatchBasicOverlayStyle.Frame,
    );
  }

  useEffect(() => {
    const initCamera = async () => {
      if (!cameraRef.current) {
        const cameraSettings = BarcodeBatch.createRecommendedCameraSettings();
        const camera = Camera.withSettings(cameraSettings);
        if (!camera) throw new Error('No camera available');
        await dataCaptureContext.setFrameSource(camera);
        await camera.switchToDesiredState(FrameSourceState.On);
        cameraRef.current = camera;
      }
    };

    void initCamera();

    const subscription = AppState.addEventListener('change', (nextAppState: AppStateStatus) => {
      if (nextAppState.match(/inactive|background/)) {
        barcodeBatchRef.current.isEnabled = false;
        cameraRef.current?.switchToDesiredState(FrameSourceState.Off);
      } else if (nextAppState === 'active') {
        barcodeBatchRef.current.isEnabled = true;
        cameraRef.current?.switchToDesiredState(FrameSourceState.On);
      }
    });

    return () => {
      subscription.remove();
      barcodeBatchRef.current.isEnabled = false;
      dataCaptureContext.removeMode(barcodeBatchRef.current);
    };
  }, []);

  return (
    <DataCaptureView
      style={{ flex: 1 }}
      context={dataCaptureContext}
      ref={view => {
        if (view && !viewRef.current) {
          view.addOverlay(overlayRef.current);
          viewRef.current = view;
        }
      }}
    />
  );
};
