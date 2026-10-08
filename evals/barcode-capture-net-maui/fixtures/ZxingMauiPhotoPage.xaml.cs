using ZXing.Net.Maui;

namespace MyApp.Views;

public record ScannedBarcode(string Value, string Format);

public partial class PhotoScanPage : ContentPage
{
    private static readonly BarcodeReaderOptions ReaderOptions = new()
    {
        Formats = BarcodeFormat.Ean13 | BarcodeFormat.DataMatrix,
        AutoRotate = true,
        TryHarder = true,
        Multiple = false,
    };

    private readonly List<ScannedBarcode> scannedBarcodes = new();

    public PhotoScanPage()
    {
        this.InitializeComponent();
    }

    private async void OnPickPhotoClicked(object? sender, EventArgs e)
    {
        var photo = await MediaPicker.Default.PickPhotoAsync();
        if (photo == null) return;

        var barcode = await this.DecodeAsync(photo);
        if (barcode == null)
        {
            this.resultLabel.Text = "No barcode found in this photo";
            return;
        }

        if (!this.scannedBarcodes.Any(b => b.Value == barcode.Value))
        {
            this.scannedBarcodes.Add(barcode);
        }
        this.resultLabel.Text = $"Last scan: {barcode.Value} ({this.scannedBarcodes.Count} total)";
    }

    private async Task<ScannedBarcode?> DecodeAsync(FileResult photo)
    {
        using var stream = await photo.OpenReadAsync();
        var results = await BarcodeReader.DecodeAsync(stream, ReaderOptions);
        var first = results?.FirstOrDefault();
        return first == null ? null : new ScannedBarcode(first.Value, first.Format.ToString());
    }
}
