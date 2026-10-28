// Motion constants. Curves from Emil Kowalski's design-engineering rules: never ease-in on UI,
// strong ease-out for anything entering or responding to a press, ease-in-out for on-screen movement.
import type { ViewStyle } from 'react-native';
import { cubicBezier, useReducedMotion } from 'react-native-reanimated';

export const EASE_OUT_CSS = cubicBezier(0.23, 1, 0.32, 1);
export const EASE_IN_OUT_CSS = cubicBezier(0.77, 0, 0.175, 1);

export const duration = { press: 120, control: 200, enter: 260 } as const;

const RISE = {
  from: { opacity: 0, transform: [{ translateY: 8 }] },
  to: { opacity: 1, transform: [{ translateY: 0 }] },
};
const FADE = { from: { opacity: 0 }, to: { opacity: 1 } };

/** Entrance for the few blocks of a screen the user arrives at occasionally (a scan result):
 *  8px rise + fade, 260ms strong ease-out, 50ms stagger. A CSS animation, so it runs on the UI thread
 *  and never takes the element out of layout. Reduced motion keeps only a short fade. */
export function useEnter(index = 0): ViewStyle {
  const reduced = useReducedMotion();
  return {
    animationName: reduced ? FADE : RISE,
    animationDuration: reduced ? 150 : duration.enter,
    animationDelay: reduced ? 0 : index * 50,
    animationTimingFunction: EASE_OUT_CSS,
    animationFillMode: 'backwards',
  } as ViewStyle;
}
