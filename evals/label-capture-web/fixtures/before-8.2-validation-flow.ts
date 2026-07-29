import {
	type DataCaptureView,
	type LabelCapture,
	type LabelCaptureValidationFlowListener,
	LabelCaptureValidationFlowOverlay,
	LabelCaptureValidationFlowSettings,
	type LabelField,
} from "@scandit/web-datacapture-label";

export async function attachValidationFlow(
	mode: LabelCapture,
	view: DataCaptureView,
) {
	const overlay =
		await LabelCaptureValidationFlowOverlay.withLabelCaptureForView(mode, view);

	const validationFlowSettings =
		await LabelCaptureValidationFlowSettings.create();
	await validationFlowSettings.setRequiredFieldErrorText(
		"This field is required",
	);
	await validationFlowSettings.setMissingFieldsHintText(
		"Please fill the missing fields",
	);
	await validationFlowSettings.setManualInputButtonText("Enter manually");
	await overlay.applySettings(validationFlowSettings);

	overlay.listener = {
		onValidationFlowLabelCaptured: (fields: LabelField[]) => {
			for (const field of fields) {
				console.log(field.name, field.text ?? field.barcode?.data);
			}
		},
	} satisfies LabelCaptureValidationFlowListener;
}
