import { CameraView, useCameraPermissions } from 'expo-camera';
import * as Haptics from 'expo-haptics';
import * as ImagePicker from 'expo-image-picker';
import { router, useFocusEffect } from 'expo-router';
import { useCallback, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Linking, StyleSheet, View } from 'react-native';

import { Button, Card, Chip, Icon, IconBadge, Notice, Pressy, Row, Screen, Segmented, Steps, T } from '../../components/ui';
import { NormaliseError, normaliseImage } from '../../features/detection/normaliseImage';
import { useCrops } from '../../features/detection/useCrops';
import { useScan } from '../../store/scan';
import { useSettings } from '../../store/settings';
import { radius, spacing, touch } from '../../theme/tokens';

type Tab = 'camera' | 'photos';

function CropPicker() {
  const { t } = useTranslation();
  const crops = useCrops();
  const lastCrop = useSettings((s) => s.lastCrop);
  const setLastCrop = useSettings((s) => s.setLastCrop);
  return (
    <Card>
      <View style={{ gap: 2 }}>
        <T v="heading">{t('crop.title')}</T>
        <T v="caption" muted>{t('crop.hint')}</T>
      </View>
      {crops.isError ? (
        <Row>
          <T v="label" muted>{t('crop.loadError')}</T>
          <Button kind="text" label={t('common.retry')} onPress={() => crops.refetch()} />
        </Row>
      ) : (
        <Row>
          {(crops.data ?? []).map((c) => (
            <Chip key={c.crop} label={c.name} selected={lastCrop === c.crop} onPress={() => setLastCrop(c.crop)} />
          ))}
          <Chip label={t('crop.notSure')} selected={lastCrop === null} onPress={() => setLastCrop(null)} />
        </Row>
      )}
    </Card>
  );
}

function SegmentedTabs({ value, onChange }: { value: Tab; onChange: (t: Tab) => void }) {
  const { t } = useTranslation();
  return (
    <Segmented
      value={value}
      onChange={onChange}
      options={[
        { key: 'camera', label: t('scan.tabCamera'), icon: 'camera-outline' },
        { key: 'photos', label: t('scan.tabPhotos'), icon: 'image-multiple-outline' },
      ]}
    />
  );
}

/** Four corner brackets: frames the leaf without drawing a box over it. */
function FrameGuide() {
  const c = { position: 'absolute' as const, width: 34, height: 34, borderColor: '#FFFFFF' };
  return (
    <View style={styles.guideFrame}>
      <View style={[c, { top: 0, left: 0, borderTopWidth: 3, borderLeftWidth: 3, borderTopLeftRadius: 20 }]} />
      <View style={[c, { top: 0, right: 0, borderTopWidth: 3, borderRightWidth: 3, borderTopRightRadius: 20 }]} />
      <View style={[c, { bottom: 0, left: 0, borderBottomWidth: 3, borderLeftWidth: 3, borderBottomLeftRadius: 20 }]} />
      <View style={[c, { bottom: 0, right: 0, borderBottomWidth: 3, borderRightWidth: 3, borderBottomRightRadius: 20 }]} />
    </View>
  );
}

function useOpenReview() {
  const setImage = useScan((s) => s.setImage);
  return async (uri: string, width: number, height: number, source: 'camera' | 'gallery') => {
    const uriOut = await normaliseImage(uri, width, height);
    setImage(uriOut, source, useSettings.getState().lastCrop);
    router.push('/review');
  };
}

function CameraTab({ onUsePhotos, onError }: { onUsePhotos: () => void; onError: (k: string) => void }) {
  const { t } = useTranslation();
  const [permission, requestPermission] = useCameraPermissions();
  const camera = useRef<CameraView>(null);
  const [ready, setReady] = useState(false);
  const [busy, setBusy] = useState(false);
  const [facing, setFacing] = useState<'back' | 'front'>('back');
  const [torch, setTorch] = useState(false);
  const [active, setActive] = useState(true);
  const openReview = useOpenReview();

  // Release the camera when the screen loses focus (SCAN_FLOW §2).
  useFocusEffect(useCallback(() => {
    setActive(true);
    return () => setActive(false);
  }, []));

  if (!permission) return null;
  if (!permission.granted) {
    return (
      <Card>
        <View style={{ alignItems: 'center', gap: spacing.md, paddingVertical: spacing.sm }}>
          <IconBadge name="camera-outline" size={56} />
          <T center>{permission.canAskAgain ? t('scan.cameraAsk') : t('scan.cameraDenied')}</T>
        </View>
        {permission.canAskAgain ? (
          <Button label={t('scan.allowCamera')} icon="camera" onPress={requestPermission} />
        ) : (
          <Button label={t('scan.openSettings')} icon="cog" onPress={() => Linking.openSettings()} />
        )}
        <Button kind="secondary" label={t('scan.usePhotos')} icon="image-multiple" onPress={onUsePhotos} />
      </Card>
    );
  }

  const capture = async () => {
    if (!ready || busy || !camera.current) return;
    setBusy(true);
    try {
      Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
      const photo = await camera.current.takePictureAsync({ quality: 0.9 });
      await openReview(photo.uri, photo.width, photo.height, 'camera');
    } catch (e) {
      onError(e instanceof NormaliseError ? `scan.${e.reason}` : 'scan.processingError');
    } finally {
      setBusy(false);
    }
  };

  return (
    <View style={styles.cameraBox}>
      {active && (
        <CameraView
          ref={camera}
          style={StyleSheet.absoluteFill}
          facing={facing}
          enableTorch={torch}
          onCameraReady={() => setReady(true)}
          onMountError={() => onError('scan.cameraUnavailable')}
        />
      )}
      <View pointerEvents="none" style={styles.guide}>
        <FrameGuide />
        <View style={styles.guideLabel}><T v="label" color="#FFFFFF">{t('scan.frameGuide')}</T></View>
      </View>
      <View style={styles.cameraControls}>
        <Pressy accessibilityRole="button" accessibilityLabel={t('scan.torch')} accessibilityState={{ checked: torch }}
          onPress={() => setTorch((v) => !v)} style={[styles.roundSmall, torch && { backgroundColor: '#FFFFFF' }]}>
          <Icon name={torch ? 'flashlight' : 'flashlight-off'} color={torch ? '#000000' : '#FFFFFF'} size={22} />
        </Pressy>
        <Pressy
          accessibilityRole="button"
          accessibilityLabel={t('scan.capture')}
          disabled={!ready || busy}
          onPress={capture}
          scaleTo={0.92}
          style={[styles.capture, { opacity: ready && !busy ? 1 : 0.5 }]}
        >
          <View style={styles.captureInner} />
        </Pressy>
        <Pressy accessibilityRole="button" accessibilityLabel={t('scan.switchCamera')}
          onPress={() => setFacing((f) => (f === 'back' ? 'front' : 'back'))} style={styles.roundSmall}>
          <Icon name="camera-flip-outline" color="#FFFFFF" size={22} />
        </Pressy>
      </View>
    </View>
  );
}

function PhotosTab({ onError }: { onError: (k: string) => void }) {
  const { t } = useTranslation();
  const [busy, setBusy] = useState(false);
  const openReview = useOpenReview();

  // System photo picker: no media-library permission is requested (ADR-002).
  const choose = async () => {
    setBusy(true);
    try {
      const res = await ImagePicker.launchImageLibraryAsync({ mediaTypes: ['images'], allowsMultipleSelection: false, quality: 1 });
      if (res.canceled || !res.assets?.length) return; // cancelled: stay silently
      const a = res.assets[0];
      if (a.mimeType && !/^image\/(jpeg|png|webp|heic|heif)$/i.test(a.mimeType)) {
        onError('scan.unsupportedType');
        return;
      }
      await openReview(a.uri, a.width, a.height, 'gallery');
    } catch (e) {
      onError(e instanceof NormaliseError ? `scan.${e.reason}` : 'scan.processingError');
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card>
      <View style={{ alignItems: 'center', gap: spacing.md, paddingTop: spacing.md }}>
        <IconBadge name="image-search-outline" size={64} />
        <T center muted>{t('scan.photosHint')}</T>
      </View>
      <Button label={t('scan.choosePhoto')} icon="image-plus" onPress={choose} loading={busy} />
      <View style={{ height: spacing.xs }} />
      <Steps items={(['one', 'two', 'four'] as const).map((k) => t(`tips.${k}`))} />
    </Card>
  );
}

export default function ScanScreen() {
  const { t } = useTranslation();
  const [tab, setTab] = useState<Tab>('camera');
  const [errorKey, setErrorKey] = useState<string | null>(null);
  const change = (next: Tab) => {
    setErrorKey(null);
    setTab(next);
  };
  return (
    <Screen>
      <CropPicker />
      <SegmentedTabs value={tab} onChange={change} />
      {errorKey && <Notice icon="alert-circle" tone="error" text={t(errorKey)} />}
      {tab === 'camera' ? (
        <CameraTab onUsePhotos={() => change('photos')} onError={setErrorKey} />
      ) : (
        <PhotosTab onError={setErrorKey} />
      )}
    </Screen>
  );
}

const styles = StyleSheet.create({
  cameraBox: { height: 460, borderRadius: radius.card, overflow: 'hidden', backgroundColor: '#0B0D0A' },
  guide: { position: 'absolute', top: 0, right: 0, bottom: 0, left: 0, alignItems: 'center', justifyContent: 'center' },
  guideFrame: { width: '74%', aspectRatio: 1 },
  guideLabel: { position: 'absolute', top: spacing.lg, backgroundColor: 'rgba(0,0,0,0.5)', paddingHorizontal: spacing.md,
    paddingVertical: spacing.xs + 2, borderRadius: radius.pill },
  cameraControls: { position: 'absolute', bottom: spacing.xl, left: 0, right: 0, flexDirection: 'row',
    justifyContent: 'space-evenly', alignItems: 'center' },
  capture: { width: touch.capture, height: touch.capture, borderRadius: touch.capture / 2, borderWidth: 4,
    borderColor: '#FFFFFF', alignItems: 'center', justifyContent: 'center' },
  captureInner: { width: touch.capture - 16, height: touch.capture - 16, borderRadius: (touch.capture - 16) / 2,
    backgroundColor: '#FFFFFF' },
  roundSmall: { width: touch.min, height: touch.min, borderRadius: touch.min / 2, backgroundColor: 'rgba(0,0,0,0.45)',
    alignItems: 'center', justifyContent: 'center' },
});
