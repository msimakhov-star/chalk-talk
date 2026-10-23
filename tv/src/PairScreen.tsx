// Pair screen: the 4-letter code in 120 pt type and one instruction line.
import React from 'react';
import {StyleSheet, Text, View} from 'react-native';
import {PHONE_URL} from './config';
import {colors} from './theme';

type Props = {code: string | null; online: boolean};

export function PairScreen({code, online}: Props) {
  return (
    <View style={styles.screen}>
      <Text style={styles.brand}>CHALK TALK</Text>
      <Text style={styles.code}>{code ?? '••••'}</Text>
      <Text style={styles.instruction}>Open {PHONE_URL} and enter this code</Text>
      <Text style={styles.hint}>Press OK on the remote to see a demo play</Text>
      <Text style={[styles.status, online ? styles.statusOnline : styles.statusOffline]}>
        {online ? 'Connected to the Chalk Talk backend' : 'Offline demo: backend not reachable, retrying'}
      </Text>
    </View>
  );
}

const styles = StyleSheet.create({
  screen: {flex: 1, backgroundColor: colors.background, alignItems: 'center', justifyContent: 'center'},
  brand: {color: colors.offense, fontSize: 32, fontWeight: '800', letterSpacing: 8},
  code: {color: colors.text, fontSize: 120, fontWeight: '800', letterSpacing: 24, marginVertical: 8},
  instruction: {color: colors.text, fontSize: 36, textAlign: 'center', paddingHorizontal: 60},
  hint: {color: colors.muted, fontSize: 28, marginTop: 24},
  status: {fontSize: 24, marginTop: 40, paddingHorizontal: 18, paddingVertical: 8, borderRadius: 16, overflow: 'hidden'},
  statusOnline: {color: colors.text, backgroundColor: colors.badge},
  statusOffline: {color: colors.background, backgroundColor: colors.warning},
});
