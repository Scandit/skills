using Scandit.DataCapture.Label.Capture;
using Scandit.DataCapture.Label.UI.Overlay;

namespace MyApp.Services;

public interface ILabelCaptureService
{
    bool IsEnabled { get; }
    void Enable();
    void Disable();
    LabelCaptureBasicOverlay BuildOverlay();
    void Subscribe(EventHandler<LabelCaptureEventArgs> handler);
    void Unsubscribe(EventHandler<LabelCaptureEventArgs> handler);
}
