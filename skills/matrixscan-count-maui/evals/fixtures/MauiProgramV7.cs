using Scandit.DataCapture.Barcode;
using Scandit.DataCapture.Core;

namespace MyApp;

// Scandit .NET MAUI SDK v7 — MatrixScan Count builder chain.
public static class MauiProgram
{
    public static MauiApp CreateMauiApp()
    {
        var builder = MauiApp.CreateBuilder();
        builder
            .UseMauiApp<App>()
            .ConfigureFonts(fonts =>
            {
                fonts.AddFont("OpenSans-Regular.ttf", "OpenSansRegular");
            })
            .UseScanditCore()
            .UseScanditBarcode(configure =>
            {
                configure.AddBarcodeCountView();
            });

        return builder.Build();
    }
}
