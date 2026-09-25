import type {
    SparkScan,
    SparkScanFeedbackDelegate,
    SparkScanView,
    SparkScanViewSettings,
} from "@scandit/web-datacapture-barcode";
import type { Color, DataCaptureContext } from "@scandit/web-datacapture-core";
import type React from "react";

declare module "react" {
    namespace JSX {
        interface IntrinsicElements {
            "spark-scan-view": React.DetailedHTMLProps<React.HTMLAttributes<SparkScanView>, SparkScanView> & {
                // Core properties for React integration
                dataCaptureContext?: DataCaptureContext | null;
                sparkScan?: SparkScan | null;
                sparkScanViewSettings?: SparkScanViewSettings | null;

                // Visibility controls
                targetModeButtonVisible?: boolean;
                scanningBehaviorButtonVisible?: boolean;
                torchControlVisible?: boolean;
                zoomSwitchControlVisible?: boolean;
                previewSizeControlVisible?: boolean;
                barcodeFindButtonVisible?: boolean;
                labelCaptureButtonVisible?: boolean;
                cameraSwitchButtonVisible?: boolean;
                previewCloseControlVisible?: boolean;
                triggerButtonVisible?: boolean;

                // Color customization
                triggerButtonCollapsedColor?: Color;
                triggerButtonExpandedColor?: Color;
                triggerButtonAnimationColor?: Color;
                triggerButtonTintColor?: Color;
                toolbarBackgroundColor?: Color;
                toolbarIconActiveTintColor?: Color;
                toolbarIconInactiveTintColor?: Color;

                feedbackDelegate?: SparkScanFeedbackDelegate | null;
            };
        }
    }
}
