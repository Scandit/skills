import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Modal, StyleSheet, Text, TouchableOpacity, View } from 'react-native';
import { SafeAreaProvider, SafeAreaView } from 'react-native-safe-area-context';
import {
  Camera,
  DataCaptureContext,
  DataCaptureView,
  FrameSourceState,
} from 'scandit-react-native-datacapture-core';
import { Symbology } from 'scandit-react-native-datacapture-barcode';
import {
  CustomBarcode,
  ExpiryDateText,
  LabelCapture,
  LabelCaptureSettings,
  LabelCaptureValidationFlowListener,
  LabelCaptureValidationFlowOverlay,
  LabelDefinition,
  LabelField,
} from 'scandit-react-native-datacapture-label';

DataCaptureContext.initialize('-- ENTER YOUR SCANDIT LICENSE KEY HERE --');
const context = DataCaptureContext.sharedInstance;

export default function App() {
  const dataCaptureViewRef = useRef<DataCaptureView | null>(null);
  const overlayRef = useRef<LabelCaptureValidationFlowOverlay | null>(null);
  const [resultText, setResultText] = useState('');
  const [modalVisible, setModalVisible] = useState(false);

  const cameraRef = useRef<Camera>(null!);
  if (!cameraRef.current) {
    const camera = Camera.withSettings(LabelCapture.createRecommendedCameraSettings());
    if (!camera) throw new Error('No camera');
    context.setFrameSource(camera);
    cameraRef.current = camera;
  }

  const labelCaptureRef = useRef<LabelCapture>(null!);
  if (!labelCaptureRef.current) {
    const barcode = CustomBarcode.initWithNameAndSymbologies('Barcode', [
      Symbology.EAN13UPCA,
      Symbology.Code128,
    ]);
    barcode.optional = false;

    const expiry = new ExpiryDateText('Expiry Date');
    expiry.optional = false;

    const label = new LabelDefinition('Perishable Product');
    label.fields = [barcode, expiry];

    const settings = LabelCaptureSettings.settingsFromLabelDefinitions([label], {});
    const labelCapture = new LabelCapture(settings);
    context.setMode(labelCapture);
    labelCaptureRef.current = labelCapture;
  }

  const listener = useMemo<LabelCaptureValidationFlowListener>(
    () => ({
      didCaptureLabelWithFields(fields: LabelField[]) {
        setResultText(
          fields
            .map((f) => `${f.name}: ${f.barcode?.data ?? f.text ?? 'N/A'}`)
            .join('\n'),
        );
        setModalVisible(true);
      },
      didSubmitManualInputForField(_field, _oldValue, _newValue) {
        // User corrected a field manually.
      },
    }),
    [],
  );

  useEffect(() => {
    void cameraRef.current.switchToDesiredState(FrameSourceState.On);
    labelCaptureRef.current.isEnabled = true;
  }, []);

  useEffect(() => {
    if (!overlayRef.current) return;
    overlayRef.current.listener = listener;
    return () => {
      if (overlayRef.current) overlayRef.current.listener = null;
    };
  }, [listener]);

  return (
    <SafeAreaProvider>
      <SafeAreaView style={styles.safeArea}>
        <DataCaptureView
          style={styles.captureView}
          context={context}
          ref={(view) => {
            if (dataCaptureViewRef.current || view === null) return;
            dataCaptureViewRef.current = view;
            const overlay = new LabelCaptureValidationFlowOverlay(labelCaptureRef.current);
            overlay.listener = listener;
            overlayRef.current = overlay;
            view.addOverlay(overlay);
          }}
        />
        <Modal visible={modalVisible} transparent animationType="fade">
          <View style={styles.modalOverlay}>
            <View style={styles.modalCard}>
              <Text style={styles.modalTitle}>LABEL CAPTURED</Text>
              <Text>{resultText}</Text>
              <TouchableOpacity
                style={styles.continueBtn}
                onPress={() => {
                  setModalVisible(false);
                  void cameraRef.current.switchToDesiredState(FrameSourceState.On);
                  labelCaptureRef.current.isEnabled = true;
                }}>
                <Text style={styles.continueText}>CONTINUE</Text>
              </TouchableOpacity>
            </View>
          </View>
        </Modal>
      </SafeAreaView>
    </SafeAreaProvider>
  );
}

const styles = StyleSheet.create({
  safeArea: { flex: 1 },
  captureView: { flex: 1 },
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.5)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  modalCard: { backgroundColor: 'white', padding: 24, borderRadius: 8, width: '85%' },
  modalTitle: { fontSize: 18, fontWeight: 'bold', marginBottom: 12 },
  continueBtn: { backgroundColor: 'black', padding: 12, marginTop: 16, borderRadius: 4 },
  continueText: { color: 'white', textAlign: 'center', fontWeight: 'bold' },
});
