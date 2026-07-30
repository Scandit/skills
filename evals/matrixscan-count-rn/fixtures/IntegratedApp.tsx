// A working MatrixScan Count integration. BarcodeCount is wired with a
// BarcodeCountView in Icon style, camera lifecycle is managed via useEffect,
// and viewListener / viewUiListener are set in the ref callback.
// Use this fixture for tests that modify or extend an existing integration.

import React, { useEffect, useRef } from 'react';
import {
  BarcodeCount,
  BarcodeCountSettings,
  BarcodeCountSession,
  BarcodeCountView,
  BarcodeCountViewStyle,
  BarcodeCountViewListener,
  BarcodeCountViewUiListener,
  Symbology,
  TrackedBarcode,
} from 'scandit-react-native-datacapture-barcode';
import {
  Camera,
  FrameSourceState,
} from 'scandit-react-native-datacapture-core';
import { DataCaptureContext } from 'scandit-react-native-datacapture-core';

DataCaptureContext.initialize('-- ENTER YOUR SCANDIT LICENSE KEY HERE --');
const dataCaptureContext = DataCaptureContext.sharedInstance;

export const IntegratedCountScreen = () => {
  const cameraRef = useRef<Camera>(null!);
  if (!cameraRef.current) {
    const camera = Camera.withSettings(BarcodeCount.createRecommendedCameraSettings());
    if (!camera) throw new Error('Camera unavailable');
    dataCaptureContext.setFrameSource(camera);
    cameraRef.current = camera;
  }

  const barcodeCountRef = useRef<BarcodeCount>(null!);
  if (!barcodeCountRef.current) {
    const settings = new BarcodeCountSettings();
    settings.enableSymbologies([
      Symbology.EAN13UPCA,
      Symbology.EAN8,
      Symbology.Code128,
    ]);

    const mode = new BarcodeCount(settings);
    mode.addListener({
      didScan: async (_: BarcodeCount, session: BarcodeCountSession) => {
        console.log(
          'Scanned:',
          session.recognizedBarcodes.map(b => b.data),
        );
      },
    });
    dataCaptureContext.addMode(mode);
    barcodeCountRef.current = mode;
  }

  const viewListenerRef = useRef<BarcodeCountViewListener | null>(null);
  if (!viewListenerRef.current) {
    viewListenerRef.current = {
      didTapRecognizedBarcode: (_view: BarcodeCountView, tb: TrackedBarcode) => {
        console.log('Tapped recognized barcode:', tb.barcode.data);
      },
      didCompleteCaptureList: (_view: BarcodeCountView) => {
        console.log('Capture list completed');
      },
    };
  }

  const viewUiListenerRef = useRef<BarcodeCountViewUiListener | null>(null);
  if (!viewUiListenerRef.current) {
    viewUiListenerRef.current = {
      didTapListButton: (_view: BarcodeCountView) => {
        console.log('List button tapped');
      },
      didTapExitButton: (_view: BarcodeCountView) => {
        cameraRef.current.switchToDesiredState(FrameSourceState.Off);
      },
    };
  }

  useEffect(() => {
    cameraRef.current.switchToDesiredState(FrameSourceState.On);
    return () => {
      dataCaptureContext.setFrameSource(null);
    };
  }, []);

  return (
    <BarcodeCountView
      style={{ flex: 1 }}
      barcodeCount={barcodeCountRef.current}
      context={dataCaptureContext}
      viewStyle={BarcodeCountViewStyle.Icon}
      ref={view => {
        if (view) {
          view.listener = viewListenerRef.current;
          view.uiListener = viewUiListenerRef.current;
        }
      }}
    />
  );
};
