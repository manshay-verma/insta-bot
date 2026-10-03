import React, { useEffect, useMemo, useRef, useState } from 'react';
import { ChevronDown, Check } from 'lucide-react';

export default function ThemedSelect({
  value,
  onChange,
  options,
  placeholder = 'Select…',
  disabled = false,
  leftIcon = null,
  ariaLabel,
}) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef(null);
  const listRef = useRef(null);

  const normalized = useMemo(() => {
    return (options || []).map((o) => {
      if (typeof o === 'string') return { value: o, label: o };
      return o;
    });
  }, [options]);

  const selected = useMemo(() => normalized.find((o) => String(o.value) === String(value)), [normalized, value]);

  useEffect(() => {
    const onDocMouseDown = (e) => {
      if (!rootRef.current) return;
      if (!rootRef.current.contains(e.target)) setOpen(false);
    };
    const onDocKeyDown = (e) => {
      if (e.key === 'Escape') setOpen(false);
    };
    document.addEventListener('mousedown', onDocMouseDown);
    document.addEventListener('keydown', onDocKeyDown);
    return () => {
      document.removeEventListener('mousedown', onDocMouseDown);
      document.removeEventListener('keydown', onDocKeyDown);
    };
  }, []);

  useEffect(() => {
    if (!open) return;
    requestAnimationFrame(() => {
      listRef.current?.focus?.();
    });
  }, [open]);

  const commit = (next) => {
    if (disabled) return;
    onChange?.(next);
    setOpen(false);
  };

  return (
    <div ref={rootRef} className="ts-root">
      <button
        type="button"
        className="ts-trigger"
        onClick={() => !disabled && setOpen((v) => !v)}
        disabled={disabled}
        aria-label={ariaLabel}
        aria-haspopup="listbox"
        aria-expanded={open}
      >
        <span className="ts-left">
          {leftIcon ? <span className="ts-leftIcon">{leftIcon}</span> : null}
          <span className={`ts-value ${selected ? '' : 'ts-placeholder'}`}>
            {selected ? selected.label : placeholder}
          </span>
        </span>
        <ChevronDown size={18} className={`ts-chevron ${open ? 'ts-chevronOpen' : ''}`} />
      </button>

      {open && (
        <div className="ts-popover" role="listbox" tabIndex={-1} ref={listRef} aria-label={ariaLabel}>
          {normalized.map((opt) => {
            const isSelected = String(opt.value) === String(value);
            const isDisabled = !!opt.disabled;
            return (
              <button
                type="button"
                key={String(opt.value)}
                className={`ts-item ${isSelected ? 'ts-itemSelected' : ''}`}
                onClick={() => !isDisabled && commit(opt.value)}
                disabled={isDisabled}
                role="option"
                aria-selected={isSelected}
              >
                <span className="ts-itemLabel">{opt.label}</span>
                {isSelected ? <Check size={16} className="ts-check" /> : <span className="ts-checkSpacer" />}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}

