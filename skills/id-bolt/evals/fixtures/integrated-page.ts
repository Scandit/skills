import {
    CancellationReason,
    DocumentSelection,
    DriverLicense,
    IdBoltSession,
    IdCard,
    Passport,
    Region,
    ReturnDataMode,
    Validators,
} from "@scandit/web-id-bolt";

const ID_BOLT_URL = "https://app.id-scanning.com";
const LICENSE_KEY = "-- ENTER YOUR SCANDIT LICENSE KEY HERE --";

async function startIdBolt() {
    const documentSelection = DocumentSelection.create({
        accepted: [
            new Passport(Region.Any),
            new IdCard(Region.Any),
            new DriverLicense(Region.Any),
        ],
    });

    const idBoltSession = IdBoltSession.create(ID_BOLT_URL, {
        licenseKey: LICENSE_KEY,
        documentSelection,
        returnDataMode: ReturnDataMode.Full,
        validation: [Validators.notExpired()],
        locale: "en-US",
        onCompletion: (result) => {
            if (result.capturedId) {
                console.log("Document type:", result.capturedId.documentType);
                console.log("Full name:", result.capturedId.fullName);
                console.log("Document number:", result.capturedId.documentNumber);
                console.log("Date of birth:", result.capturedId.dateOfBirth);
                console.log("Date of expiry:", result.capturedId.dateOfExpiry);
            }
        },
        onCancellation: (reason) => {
            switch (reason) {
                case CancellationReason.UserClosed:
                    console.log("User closed the scanning window");
                    break;
                case CancellationReason.ServiceStartFailure:
                    console.error("ID Bolt service failed to start");
                    break;
            }
        },
    });

    // Opens the hosted pop-up; resolves when the flow ends.
    await idBoltSession.start();
}

// ID Bolt must be started from a user gesture (the pop-up requires it).
document.getElementById("scan-id")?.addEventListener("click", () => {
    startIdBolt().catch(console.error);
});
