"use client";

import { useSyncExternalStore } from "react";

const storageKey = "digemid:ragas-default";
const changeEvent = "digemid:ragas-default-changed";
let unsavedPreference: boolean | undefined;

function subscribe(onChange: () => void) {
  function onStorage(event: StorageEvent) {
    if (event.key === storageKey || event.key === null) onChange();
  }
  window.addEventListener("storage", onStorage);
  window.addEventListener(changeEvent, onChange);
  return () => {
    window.removeEventListener("storage", onStorage);
    window.removeEventListener(changeEvent, onChange);
  };
}

function getPreference() {
  if (unsavedPreference !== undefined) return unsavedPreference;
  try {
    return window.localStorage.getItem(storageKey) === "true";
  } catch {
    return false;
  }
}

export function setRagasDefault(enabled: boolean) {
  try {
    window.localStorage.setItem(storageKey, String(enabled));
    unsavedPreference = undefined;
  } catch {
    unsavedPreference = enabled;
  }
  window.dispatchEvent(new Event(changeEvent));
}

export function useRagasDefault() {
  return useSyncExternalStore(subscribe, getPreference, () => false);
}
