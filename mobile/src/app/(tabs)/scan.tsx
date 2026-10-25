import { CameraView, useCameraPermissions } from 'expo-camera';
import * as Haptics from 'expo-haptics';
import * as ImagePicker from 'expo-image-picker';
import { router, useFocusEffect } from 'expo-router';
import { useCallback, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Linking, Pressable, StyleSheet, View } from 'react-native';

import { Button, Card, Chip, Icon, Notice, Row, Screen, T } from '../../components/ui';
import { NormaliseError, normaliseImage } from '../../features/detection/normaliseImage';
import { useCrops } from '../../features/detection/useCrops';
import { useScan } from '../../store/scan';
import { useSettings } from '../../store/settings';
import { radius, spacing, touch } from '../../theme/tokens';
import { useTheme } from '../../theme/useTheme';

type Tab = 'camera' | 'photos';

function CropPicker() {
  const { t } = useTranslation();
  const crops = useCrops();
  const lastCrop = useSettings((s) => s.lastCrop);
  const setLastCrop = useSettings((s) => s.setLastCrop);
  return (
    <Card>
      <T v="heading">{t('crop.title')}</T>
      <T v="caption" muted>{t('crop.hint')}</T>
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
  const { colors, type, borderWidth } = useTheme();
  return (
    <View style={[styles.segment, { borderColor: colors.primary, borderWidth: borderWidth + 1 }]} accessibilityRole="tablist">
      {(['camera', 'photos'] as const).map((tab) => {
        const selected = value === tab;
        return (
          <Pressable
            key={tab}
            accessibilityRole="tab"
            accessibilityState={{ selected }}
            onPress={() => onChange(tab)}
            style={[styles.segmentItem, { backgroundColor: selected ? colors.primary : colors.surface }]}
          >
            <Icon name={tab === 'camera' ? 'camera' : 'image-multiple'} color={selected ? colors.onPrimary : colors.primary} />
            <T v="heading" color={selected ? colors.onPrimary : colors.primary}>
              {t(tab === 'camera' ? 'scan.tabCamera' : 'scan.tabPhotos')}
            </T>
          </Pressable>
        );
      })}
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
  const { colors } = useTheme();
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
        <T>{permission.canAskAgain ? t('scan.cameraAsk') : t('scan.cameraDenied')}</T>
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
    <View style={[styles.cameraBox, { borderColor: colors.border }]}>
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
        <View style={[styles.guideFrame, { borderColor: '#FFFFFF' }]} />
        <View style={styles.guideLabel}><T v="label" color="#FFFFFF">{t('scan.frameGuide')}</T></View>
      </View>
      <View style={styles.cameraControls}>
        <Pressable accessibilityLabel={t('scan.torch')} onPress={() => setTorch((v) => !v)} style={styles.roundSmall}>
          <Icon name={torch ? 'flashlight' : 'flashlight-off'} color="#FFFFFF" />
        </Pressable>
        <Pressable
          accessibilityRole="button"
          accessibilityLabel={t('scan.capture')}
          disabled={!ready || busy}
          onPress={capture}
          style={[styles.capture, { opacity: ready && !busy ? 1 : 0.5 }]}
        />
        <Pressable accessibilityLabel={t('scan.switchCamera')} onPress={() => setFacing((f) => (f === 'back' ? 'front' : 'back'))}
          style={styles.roundSmall}>
          <Icon name="camera-flip" color="#FFFFFF" />
        </Pressable>
      </View>
    </View>
  );
}

function PhotosTab({ onError }: { onError: (k: string) => void }) {
  const { t } = useTranslation();
  const { colors } = useTheme();
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
      <View style={{ alignItems: 'center', paddingVertical: spacing.lg }}>
        <Icon name="image-search" size={64} color={colors.primary} />
      </View>
      <T center>{t('scan.photosHint')}</T>
      <Button label={t('scan.choosePhoto')} icon="image-plus" onPress={choose} loading={busy} />
      {(['one', 'two', 'four'] as const).map((k) => (
        <Row key={k} style={{ flexWrap: 'nowrap', alignItems: 'flex-start' }}>
          <Icon name="check-circle" color={colors.primary} size={20} />
          <T v="label">{t(`tips.${k}`)}</T>
        </Row>
      ))}
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
  segment: { flexDirection: 'row', borderRadius: radius.button, overflow: 'hidden' },
  segmentItem: { flex: 1, minHeight: touch.min + 4, flexDirection: 'row', alignItems: 'center', justifyContent: 'center',
    gap: spacing.sm },
  cameraBox: { height: 460, borderRadius: radius.card, overflow: 'hidden', backgroundColor: '#000', borderWidth: 1 },
  guide: { position: 'absolute', top: 0, right: 0, bottom: 0, left: 0, alignItems: 'center', justifyContent: 'center' },
  guideFrame: { width: '78%', aspectRatio: 1, borderWidth: 3, borderRadius: 24, borderStyle: 'dashed' },
  guideLabel: { position: 'absolute', top: spacing.lg, backgroundColor: 'rgba(0,0,0,0.55)', paddingHorizontal: spacing.md,
    paddingVertical: spacing.xs, borderRadius: 8 },
  cameraControls: { position: 'absolute', bottom: spacing.lg, left: 0, right: 0, flexDirection: 'row',
    justifyContent: 'space-evenly', alignItems: 'center' },
  capture: { width: touch.capture, height: touch.capture, borderRadius: touch.capture / 2, backgroundColor: '#FFFFFF',
    borderWidth: 6, borderColor: 'rgba(255,255,255,0.45)' },
  roundSmall: { width: touch.min, height: touch.min, borderRadius: touch.min / 2, backgroundColor: 'rgba(0,0,0,0.5)',
    alignItems: 'center', justifyContent: 'center' },
});
