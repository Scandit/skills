import { toastController } from '@ionic/vue';
import { Capacitor } from '@capacitor/core';
import { useRouter } from 'vue-router';
import { InviteLinkService } from '@/services/inviteLinkService';
import config from '@/config';

/**
 * Native QR scanning (Capacitor + ML Kit). Opens the platform barcode scanner,
 * then routes recognised content into the app:
 *  - InterPoll invite links (`/join/{type}/{id}#key`, full URL or path) → the
 *    JoinPrivatePage, which auto-joins from the key in the fragment.
 *  - Other same-origin app URLs → the corresponding in-app route.
 *
 * QR scanning is native-only; `isSupported` is false in the browser so callers
 * can hide the entry point.
 */
export function useQrScan() {
  const router = useRouter();
  const isSupported = Capacitor.isNativePlatform();

  async function toast(message: string, color: 'success' | 'danger' | 'warning') {
    const t = await toastController.create({ message, duration: 2200, position: 'bottom', color });
    await t.present();
  }

  /**
   * Turn a scanned string into an in-app navigation. Returns true if it was
   * recognised and handled.
   */
  function routeScanned(raw: string): boolean {
    const text = raw.trim();

    // 1. Invite link (full URL or path-only). parseInviteLink validates shape.
    const invite = InviteLinkService.parseInviteLink(text);
    if (invite) {
      router.push(`/join/${invite.type}/${encodeURIComponent(invite.id)}#${invite.key}`);
      return true;
    }

    // 2. Any other URL pointing at our own web origin → navigate to its path.
    try {
      if (text.startsWith('http://') || text.startsWith('https://')) {
        const u = new URL(text);
        const canonical = new URL(config.web.origin);
        if (u.host === canonical.host || u.hostname === 'localhost') {
          router.push(`${u.pathname}${u.search}${u.hash}`);
          return true;
        }
      }
    } catch {
      /* not a URL */
    }

    return false;
  }

  async function scan(): Promise<void> {
    if (!isSupported) {
      await toast('QR scanning is only available in the app', 'warning');
      return;
    }

    try {
      const { BarcodeScanner, BarcodeFormat } = await import('@capacitor-mlkit/barcode-scanning');

      // On Android the ML Kit scanner ships as an on-demand Google Play module.
      // Ensure it's installed before the first scan so the call doesn't fail.
      try {
        const { available } = await BarcodeScanner.isGoogleBarcodeScannerModuleAvailable();
        if (!available) {
          await BarcodeScanner.installGoogleBarcodeScannerModule();
        }
      } catch {
        /* iOS / not applicable — scan() works without the module */
      }

      const { barcodes } = await BarcodeScanner.scan({ formats: [BarcodeFormat.QrCode] });
      if (!barcodes.length) return; // user cancelled / nothing found

      const value = barcodes[0].rawValue ?? barcodes[0].displayValue ?? '';
      if (!value) {
        await toast('Could not read that QR code', 'danger');
        return;
      }

      if (!routeScanned(value)) {
        await toast('This QR code isn’t an InterPoll invite', 'warning');
      }
    } catch (err) {
      const msg = (err as Error)?.message ?? '';
      if (/cancel/i.test(msg)) return; // user dismissed the scanner
      await toast('Scanning failed. Check camera permission.', 'danger');
    }
  }

  return { isSupported, scan, routeScanned };
}
