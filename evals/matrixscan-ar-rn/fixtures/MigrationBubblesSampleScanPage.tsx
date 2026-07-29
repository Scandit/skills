import React, { useState, useEffect, useRef, useMemo } from 'react';
import { AppState, AppStateStatus, Dimensions } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { SafeAreaView } from 'react-native-safe-area-context';
import {
  BarcodeBatch,
  BarcodeBatchAdvancedOverlay,
  BarcodeBatchBasicOverlay,
  BarcodeBatchBasicOverlayStyle,
  BarcodeBatchListener,
  BarcodeBatchSettings,
  Symbology,
  TrackedBarcode,
} from 'scandit-react-native-datacapture-barcode';
import {
  Anchor,
  Camera,
  DataCaptureView,
  FrameSourceState,
  MeasureUnit,
  NumberWithUnit,
  PointWithUnit,
  Quadrilateral,
} from 'scandit-react-native-datacapture-core';

import { ARView } from './ARView';
import Freeze from './Freeze.svg';
import { styles } from './styles';
import Unfreeze from './Unfreeze.svg';
import dataCaptureContext from './CaptureContext';

export const ScanPage = () => {
  const navigation = useNavigation();

  const viewRef = useRef<DataCaptureView>(null);
  const cameraRef = useRef<Camera | null>(null);

  const barcodeBatchRef = useRef<BarcodeBatch>(null!);
  if (!barcodeBatchRef.current) {
    barcodeBatchRef.current = setupBarcodeBatch();
  }

  const trackedBarcodesRef = useRef<Record<string, any>>({});
  const advancedOverlayRef = useRef<BarcodeBatchAdvancedOverlay>(null!);
  if (!advancedOverlayRef.current) {
    advancedOverlayRef.current = setupAdvancedOverlay();
  }
  const basicOverlayRef = useRef<BarcodeBatchBasicOverlay>(null!);
  if (!basicOverlayRef.current) {
    basicOverlayRef.current = setupBasicOverlay();
  }

  const barcodeBatchListenerRef = useRef<BarcodeBatchListener | null>(null);
  const isScanningRef = useRef(true);

  const [isScanning, setIsScanning] = useState(true);

  function setupBarcodeBatch(): BarcodeBatch {
    // We create a barcode batch settings to enable the symbologies we want to track.
    const settings = new BarcodeBatchSettings();
    settings.enableSymbologies([
      Symbology.EAN13UPCA,
      Symbology.EAN8,
      Symbology.UPCE,
      Symbology.Code39,
      Symbology.Code128,
    ]);

    const batch = new BarcodeBatch(settings);
    batch.addListener({
      async didUpdateSession(...args) {
        if (!barcodeBatchListenerRef.current || !barcodeBatchListenerRef.current.didUpdateSession) {
          return;
        }
        // We have to call the listeners through the ref to ensure that the latest listener is used.
        return barcodeBatchListenerRef.current.didUpdateSession(...args);
      },
    });

    // Set the barcode batch mode to the data capture context.
    dataCaptureContext.setMode(batch);

    return batch;
  }

  async function setupCamera(): Promise<Camera> {
    const cameraSettings = BarcodeBatch.createRecommendedCameraSettings();
    const newCamera = Camera.withSettings(cameraSettings);
    if (!newCamera) {
      throw new Error('No camera available');
    }
    // Set the camera as the frame source of the data capture context.
    await dataCaptureContext.setFrameSource(newCamera);
    // Guard against the screen losing focus or going to background while the camera was being configured.
    if (navigation.isFocused()) {
      await newCamera.switchToDesiredState(FrameSourceState.On);
    }
    return newCamera;
  }

  useEffect(() => {
    const initCamera = async () => {
      if (!cameraRef.current) {
        cameraRef.current = await setupCamera();
      }
    };

    initCamera();

    const handleAppStateChange = (nextAppState: AppStateStatus) => {
      // If the app is going to the background or inactive state, we stop the capture.
      if (nextAppState.match(/inactive|background/)) {
        stopCapture();
      } else if (nextAppState === 'active' && navigation.isFocused()) {
        if (isScanningRef.current) {
          startCapture();
        }
      }
    };

    const handleAppStateChangeSubscription = AppState.addEventListener('change', handleAppStateChange);
    return () => {
      handleAppStateChangeSubscription.remove();
      stopCapture();
      dataCaptureContext.removeMode(barcodeBatchRef.current);
    };
  }, []);

  const startCapture = () => {
    barcodeBatchRef.current.isEnabled = true;
    startCamera();
  };

  const stopCapture = () => {
    barcodeBatchRef.current.isEnabled = false;
    stopCamera();
  };

  const stopCamera = () => {
    if (cameraRef.current) {
      cameraRef.current.switchToDesiredState(FrameSourceState.Off);
    }
  };

  const startCamera = () => {
    if (cameraRef.current) {
      cameraRef.current.switchToDesiredState(FrameSourceState.On);
    }
  };

  function setupBasicOverlay(): BarcodeBatchBasicOverlay {
    if (!barcodeBatchRef.current) {
      throw new Error('Failed to initialize overlay');
    }
    // We create an overlay to highlight the barcodes.
    return new BarcodeBatchBasicOverlay(barcodeBatchRef.current, BarcodeBatchBasicOverlayStyle.Dot);
  }

  function setupAdvancedOverlay(): BarcodeBatchAdvancedOverlay {
    if (!barcodeBatchRef.current) {
      throw new Error('Failed to initialize overlay');
    }

    // We create an overlay for the bubbles.
    const overlay = new BarcodeBatchAdvancedOverlay(barcodeBatchRef.current);

    overlay.listener = {
      anchorForTrackedBarcode: () => Anchor.TopCenter,
      offsetForTrackedBarcode: () =>
        new PointWithUnit(new NumberWithUnit(0, MeasureUnit.Fraction), new NumberWithUnit(-1, MeasureUnit.Fraction)),
    };
    return overlay;
  }

  const getQuadrilateralWidth = (quadrilateral: Quadrilateral): number => {
    return Math.max(
      Math.abs(quadrilateral.topRight.x - quadrilateral.topLeft.x),
      Math.abs(quadrilateral.bottomRight.x - quadrilateral.bottomLeft.x)
    );
  };

  const updateView = (trackedBarcode: TrackedBarcode, viewLocation: Quadrilateral) => {
    const shouldBeShown = getQuadrilateralWidth(viewLocation) > Dimensions.get('window').width * 0.1;

    if (!shouldBeShown) {
      trackedBarcodesRef.current = {
        ...trackedBarcodesRef.current,
        [trackedBarcode.identifier]: null,
      };
      return;
    }

    const barcodeData = trackedBarcode.barcode.data;

    if (!barcodeData) {
      return;
    }

    const didViewChange =
      JSON.stringify(trackedBarcodesRef.current[trackedBarcode.identifier]) !== JSON.stringify(barcodeData);
    if (didViewChange) {
      trackedBarcodesRef.current = {
        ...trackedBarcodesRef.current,
        [trackedBarcode.identifier]: barcodeData,
      };

      const props = {
        barcodeData,
        stock: { shelf: 4, backRoom: 8 },
      };

      advancedOverlayRef.current?.setViewForTrackedBarcode(new ARView(props), trackedBarcode).catch(console.warn);
    }
  };

  const toggleScan = () => {
    const isScanning = barcodeBatchRef.current.isEnabled === true;
    const newState = !isScanning;
    setIsScanning(newState);
    isScanningRef.current = newState;
    barcodeBatchRef.current.isEnabled = newState;

    if (newState === true) {
      startCamera();
    } else {
      stopCamera();
    }
  };

  barcodeBatchListenerRef.current = {
    async didUpdateSession(_barcodeBatch, session, _getFrameData) {
      const updatedTrackedBarcodes = { ...trackedBarcodesRef.current };
      session.removedTrackedBarcodes.forEach(identifier => {
        updatedTrackedBarcodes[identifier] = null;
      });

      Object.values(session.trackedBarcodes).forEach(trackedBarcode => {
        viewRef.current?.viewQuadrilateralForFrameQuadrilateral(trackedBarcode.location).then(location => {
          updateView(trackedBarcode, location);
        });
      });
      trackedBarcodesRef.current = updatedTrackedBarcodes;
    },
  };

  return (
    <>
      <DataCaptureView
        style={styles.dataCaptureView}
        context={dataCaptureContext}
        ref={(view: DataCaptureView | null) => {
          if (view && !viewRef.current) {
            view.addOverlay(basicOverlayRef.current);
            view.addOverlay(advancedOverlayRef.current);
            viewRef.current = view;
          }
        }}
      />
      <SafeAreaView style={styles.toggleContainer}>
        {isScanning ? <Freeze onPress={toggleScan} /> : <Unfreeze onPress={toggleScan} />}
      </SafeAreaView>
    </>
  );
};
