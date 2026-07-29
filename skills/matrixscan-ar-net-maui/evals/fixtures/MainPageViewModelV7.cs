using System.Collections.ObjectModel;
using System.ComponentModel;

using Scandit.DataCapture.Barcode.Ar.Capture;
using Scandit.DataCapture.Barcode.Ar.UI;
using Scandit.DataCapture.Barcode.Data;
using Scandit.DataCapture.Core.Capture;

namespace MyApp.ViewModels;

public class MainPageViewModel : INotifyPropertyChanged
{
    public const string SCANDIT_LICENSE_KEY = "-- ENTER YOUR SCANDIT LICENSE KEY HERE --";

    public DataCaptureContext DataCaptureContext { get; }
    public BarcodeAr BarcodeAr { get; }
    public BarcodeArViewSettings ViewSettings { get; } = new();

    public ObservableCollection<string> ScanResults { get; } = new();

    public event PropertyChangedEventHandler? PropertyChanged;

    public MainPageViewModel()
    {
        this.DataCaptureContext = DataCaptureContext.ForLicenseKey(SCANDIT_LICENSE_KEY);

        var settings = new BarcodeArSettings();
        settings.EnableSymbologies(new HashSet<Symbology>
        {
            Symbology.Ean13Upca,
            Symbology.Code128,
        });

        this.BarcodeAr = new BarcodeAr(this.DataCaptureContext, settings);
        this.BarcodeAr.SessionUpdated += this.OnSessionUpdated;
    }

    private void OnSessionUpdated(object? sender, BarcodeArEventArgs args)
    {
        var added = args.Session.AddedTrackedBarcodes
            .Select(tb => tb.Barcode.Data ?? string.Empty)
            .ToList();
        if (added.Count == 0) return;

        MainThread.BeginInvokeOnMainThread(() =>
        {
            foreach (var data in added) this.ScanResults.Add(data);
        });
    }
}
