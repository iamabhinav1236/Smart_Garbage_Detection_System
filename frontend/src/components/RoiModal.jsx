import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  X, Save, RotateCcw, Undo2, RefreshCw, Camera, Trash2,
  CheckCircle2, AlertTriangle, Info, Crosshair,
} from 'lucide-react';
import { binService } from '../services/api';
import { useNotification } from '../context/NotificationContext';

// Canvas space matches the backend analysis frame (640x480), so points are saved as-is.
const CANVAS_W = 640;
const CANVAS_H = 480;
const HIT_RADIUS = 12;

const ZONES = {
  BIN: { label: 'Bin interior', color: '#06b6d4', fill: 'rgba(6, 182, 212, 0.22)', prefix: 'P' },
  FLOOR: { label: 'Floor zone', color: '#f59e0b', fill: 'rgba(245, 158, 11, 0.18)', prefix: 'F' },
};

const STEP_HINTS = {
  BIN: 'Click around the inside of the bin opening, from its rim down to its base. Use at least 3 points; 4–6 usually work best.',
  FLOOR: 'Optional: outline the ground around the bin where litter or overflow lands. The bin itself is excluded automatically.',
  REFERENCE: 'Capture a photo of the bin while it is empty. Live frames are compared against it, which makes fill readings much more accurate.',
};

const parsePoints = (roi) => {
  if (!roi) return [];
  try {
    const pts = JSON.parse(roi);
    if (!Array.isArray(pts)) return [];
    const normalized = pts.every(([x, y]) => x <= 1 && y <= 1);
    return pts.map(([x, y]) => [
      Math.round(Math.min(CANVAS_W, Math.max(0, normalized ? x * CANVAS_W : x))),
      Math.round(Math.min(CANVAS_H, Math.max(0, normalized ? y * CANVAS_H : y))),
    ]);
  } catch {
    return [];
  }
};

const RoiModal = ({ bin, onClose, onSaved }) => {
  const { showToast } = useNotification();
  const canvasRef = useRef(null);
  const imageRef = useRef(null);
  const dragRef = useRef(null); // { zone, index }

  const [step, setStep] = useState('BIN'); // 'BIN' | 'FLOOR' | 'REFERENCE'
  const [points, setPoints] = useState(() => ({
    BIN: parsePoints(bin.bin_roi),
    FLOOR: parsePoints(bin.floor_roi),
  }));
  const [history, setHistory] = useState([]);
  const [dirty, setDirty] = useState(false);
  const [cursor, setCursor] = useState(null);
  const [hovered, setHovered] = useState(null); // { zone, index }
  const [dragging, setDragging] = useState(false);
  const [frameStatus, setFrameStatus] = useState('loading'); // 'loading' | 'ready' | 'error'
  const [saving, setSaving] = useState(false);
  const [reference, setReference] = useState({ has_reference: false, captured_at: null });
  const [refBusy, setRefBusy] = useState(false);

  const editZone = step === 'REFERENCE' ? null : step;
  const binValid = points.BIN.length >= 3;
  const floorValid = points.FLOOR.length === 0 || points.FLOOR.length >= 3;

  // ---------- Data loading ----------
  const fetchFrame = useCallback(() => {
    const img = new Image();
    img.crossOrigin = 'anonymous';
    img.onload = () => {
      imageRef.current = img;
      setFrameStatus('ready');
    };
    img.onerror = () => setFrameStatus('error');
    img.src = binService.getFrameUrl(bin.id);
  }, [bin.id]);

  const loadFrame = useCallback(() => {
    setFrameStatus('loading');
    fetchFrame();
  }, [fetchFrame]);

  useEffect(() => {
    fetchFrame();
    binService.getEmptyReference(bin.id)
      .then((res) => setReference(res.data))
      .catch(() => {});
  }, [bin.id, fetchFrame]);

  // ---------- Drawing ----------
  const draw = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, CANVAS_W, CANVAS_H);

    if (frameStatus === 'ready' && imageRef.current) {
      ctx.drawImage(imageRef.current, 0, 0, CANVAS_W, CANVAS_H);
    } else {
      ctx.fillStyle = '#0f172a';
      ctx.fillRect(0, 0, CANVAS_W, CANVAS_H);
    }

    // Draw the inactive zone first so the one being edited sits on top
    const order = editZone === 'BIN' ? ['FLOOR', 'BIN'] : ['BIN', 'FLOOR'];
    order.forEach((zone) => {
      const pts = points[zone];
      if (!pts.length) return;
      const { color, fill, prefix } = ZONES[zone];
      const active = zone === editZone;

      ctx.globalAlpha = active || !editZone ? 1 : 0.45;
      ctx.lineWidth = active ? 2.5 : 2;
      ctx.strokeStyle = color;
      ctx.fillStyle = fill;
      ctx.beginPath();
      ctx.moveTo(pts[0][0], pts[0][1]);
      pts.slice(1).forEach(([x, y]) => ctx.lineTo(x, y));
      if (pts.length >= 3) {
        ctx.closePath();
        ctx.fill();
      }
      ctx.stroke();

      // Preview of the next segment while placing points
      if (active && cursor && !dragRef.current && !hovered) {
        const [lx, ly] = pts[pts.length - 1];
        ctx.setLineDash([6, 6]);
        ctx.beginPath();
        ctx.moveTo(lx, ly);
        ctx.lineTo(cursor[0], cursor[1]);
        if (pts.length >= 2) ctx.lineTo(pts[0][0], pts[0][1]);
        ctx.stroke();
        ctx.setLineDash([]);
      }

      pts.forEach(([x, y], idx) => {
        const isHover = hovered && hovered.zone === zone && hovered.index === idx;
        ctx.beginPath();
        ctx.arc(x, y, isHover ? 8 : 5.5, 0, Math.PI * 2);
        ctx.fillStyle = color;
        ctx.fill();
        ctx.lineWidth = 2;
        ctx.strokeStyle = '#0b0f19';
        ctx.stroke();

        if (active) {
          ctx.font = '600 11px sans-serif';
          ctx.lineWidth = 3;
          ctx.strokeStyle = 'rgba(11, 15, 25, 0.85)';
          ctx.strokeText(`${prefix}${idx + 1}`, x + 9, y - 7);
          ctx.fillStyle = '#ffffff';
          ctx.fillText(`${prefix}${idx + 1}`, x + 9, y - 7);
        }
      });
      ctx.globalAlpha = 1;
    });
  }, [points, editZone, cursor, hovered, frameStatus]);

  useEffect(() => {
    draw();
  }, [draw]);

  // ---------- Editing helpers ----------
  const commit = (next) => {
    setHistory((h) => [...h.slice(-49), points]);
    setPoints(next);
    setDirty(true);
  };

  const toCanvas = (e) => {
    const rect = canvasRef.current.getBoundingClientRect();
    const x = ((e.clientX - rect.left) / rect.width) * CANVAS_W;
    const y = ((e.clientY - rect.top) / rect.height) * CANVAS_H;
    return [
      Math.round(Math.min(CANVAS_W, Math.max(0, x))),
      Math.round(Math.min(CANVAS_H, Math.max(0, y))),
    ];
  };

  const findPoint = ([x, y]) => {
    if (!editZone) return null;
    const rect = canvasRef.current.getBoundingClientRect();
    const radius = HIT_RADIUS * (CANVAS_W / rect.width);
    const pts = points[editZone];
    for (let i = pts.length - 1; i >= 0; i--) {
      if (Math.hypot(pts[i][0] - x, pts[i][1] - y) <= radius) return { zone: editZone, index: i };
    }
    return null;
  };

  const handlePointerDown = (e) => {
    if (!editZone || e.button === 2) return;
    const pos = toCanvas(e);
    const hit = findPoint(pos);
    if (hit) {
      dragRef.current = hit;
      setDragging(true);
      setHistory((h) => [...h.slice(-49), points]);
      canvasRef.current.setPointerCapture(e.pointerId);
      return;
    }
    commit({ ...points, [editZone]: [...points[editZone], pos] });
  };

  const handlePointerMove = (e) => {
    const pos = toCanvas(e);
    setCursor(pos);
    if (dragRef.current) {
      const { zone, index } = dragRef.current;
      setPoints((prev) => ({
        ...prev,
        [zone]: prev[zone].map((p, i) => (i === index ? pos : p)),
      }));
      setDirty(true);
      return;
    }
    setHovered(findPoint(pos));
  };

  const handlePointerUp = (e) => {
    if (dragRef.current) {
      dragRef.current = null;
      setDragging(false);
      canvasRef.current.releasePointerCapture(e.pointerId);
    }
  };

  const handleContextMenu = (e) => {
    e.preventDefault();
    const hit = findPoint(toCanvas(e));
    if (hit) {
      commit({ ...points, [hit.zone]: points[hit.zone].filter((_, i) => i !== hit.index) });
      setHovered(null);
    }
  };

  const handleUndo = useCallback(() => {
    if (!history.length) return;
    setPoints(history[history.length - 1]);
    setHistory(history.slice(0, -1));
    setDirty(true);
  }, [history]);

  const handleClear = () => {
    if (!editZone || !points[editZone].length) return;
    commit({ ...points, [editZone]: [] });
  };

  const requestClose = useCallback(() => {
    if (dirty && !window.confirm('Discard unsaved calibration changes?')) return;
    onClose();
  }, [dirty, onClose]);

  useEffect(() => {
    const onKey = (e) => {
      if (e.key === 'Escape') requestClose();
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'z') {
        e.preventDefault();
        handleUndo();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [requestClose, handleUndo]);

  // ---------- Persistence ----------
  const handleSave = async () => {
    if (!binValid) {
      setStep('BIN');
      showToast('The bin interior needs at least 3 points', 'error');
      return;
    }
    if (!floorValid) {
      setStep('FLOOR');
      showToast('The floor zone needs at least 3 points (or clear it)', 'error');
      return;
    }
    setSaving(true);
    try {
      await binService.updateRoi(bin.id, {
        bin_roi: JSON.stringify(points.BIN),
        floor_roi: JSON.stringify(points.FLOOR),
      });
      showToast('Calibration saved. Detection updates within a few seconds.', 'success');
      setDirty(false);
      if (onSaved) onSaved();
      onClose();
    } catch {
      showToast('Failed to save calibration', 'error');
    } finally {
      setSaving(false);
    }
  };

  const handleCaptureReference = async () => {
    setRefBusy(true);
    try {
      const res = await binService.captureEmptyReference(bin.id);
      setReference(res.data);
      loadFrame();
      showToast('Empty-bin reference captured', 'success');
    } catch (err) {
      showToast(err.response?.data?.detail || 'Could not capture reference', 'error');
    } finally {
      setRefBusy(false);
    }
  };

  const handleClearReference = async () => {
    setRefBusy(true);
    try {
      const res = await binService.clearEmptyReference(bin.id);
      setReference(res.data);
      showToast('Reference cleared. Using texture analysis instead.', 'info');
    } catch {
      showToast('Could not clear reference', 'error');
    } finally {
      setRefBusy(false);
    }
  };

  // ---------- Render ----------
  const steps = [
    { key: 'BIN', title: 'Bin interior', sub: binValid ? `${points.BIN.length} points` : 'Required', done: binValid, color: ZONES.BIN.color },
    { key: 'FLOOR', title: 'Floor zone', sub: points.FLOOR.length ? (floorValid ? `${points.FLOOR.length} points` : 'Needs 3+ points') : 'Optional', done: points.FLOOR.length >= 3, warn: !floorValid, color: ZONES.FLOOR.color },
    { key: 'REFERENCE', title: 'Empty reference', sub: reference.has_reference ? 'Captured' : 'Recommended', done: reference.has_reference, color: 'var(--primary)' },
  ];

  const cursorClass = !editZone ? '' : dragging ? 'dragging' : hovered ? 'grab' : 'crosshair';

  return (
    <div className="modal-overlay" onMouseDown={(e) => e.target === e.currentTarget && requestClose()}>
      <div className="modal-card roi-modal" role="dialog" aria-modal="true" aria-labelledby="roi-modal-title">
        <div className="roi-header">
          <div>
            <h3 id="roi-modal-title">Calibrate detection zones</h3>
            <p>{bin.bin_id} · {bin.name}</p>
          </div>
          <button className="roi-icon-btn" onClick={requestClose} aria-label="Close">
            <X size={18} />
          </button>
        </div>

        <div className="roi-steps" role="tablist">
          {steps.map((s, i) => (
            <button
              key={s.key}
              role="tab"
              aria-selected={step === s.key}
              className={`roi-step ${step === s.key ? 'active' : ''}`}
              style={{ '--step-color': s.color }}
              onClick={() => setStep(s.key)}
            >
              <span className={`roi-step-index ${s.done ? 'done' : ''} ${s.warn ? 'warn' : ''}`}>
                {s.done ? <CheckCircle2 size={16} /> : s.warn ? <AlertTriangle size={14} /> : i + 1}
              </span>
              <span className="roi-step-text">
                <strong>{s.title}</strong>
                <small>{s.sub}</small>
              </span>
            </button>
          ))}
        </div>

        <div className="roi-hint">
          <Info size={15} />
          <span>{STEP_HINTS[step]}</span>
        </div>

        <div className={`roi-canvas-container ${cursorClass}`}>
          <canvas
            ref={canvasRef}
            width={CANVAS_W}
            height={CANVAS_H}
            onPointerDown={handlePointerDown}
            onPointerMove={handlePointerMove}
            onPointerUp={handlePointerUp}
            onPointerLeave={() => { setCursor(null); setHovered(null); }}
            onContextMenu={handleContextMenu}
          />
          {frameStatus !== 'ready' && (
            <div className="roi-canvas-status">
              {frameStatus === 'loading' ? (
                <><RefreshCw size={20} className="spin" /> Loading camera frame…</>
              ) : (
                <>
                  <AlertTriangle size={20} />
                  Couldn't load a camera frame. Is monitoring running for this bin?
                  <button className="btn btn-secondary btn-sm" onClick={loadFrame}>Try again</button>
                </>
              )}
            </div>
          )}
          <button className="roi-refresh-btn" onClick={loadFrame} title="Grab a fresh frame">
            <RefreshCw size={14} /> Refresh frame
          </button>
        </div>

        {step === 'REFERENCE' ? (
          <div className="roi-reference-panel">
            <div className={`roi-reference-status ${reference.has_reference ? 'ok' : ''}`}>
              {reference.has_reference ? <CheckCircle2 size={18} /> : <Camera size={18} />}
              <div>
                <strong>{reference.has_reference ? 'Reference captured' : 'No reference yet'}</strong>
                <small>
                  {reference.has_reference
                    ? `Taken ${new Date(reference.captured_at).toLocaleString()}. Recapture it if the camera moves or the lighting changes a lot.`
                    : 'Without a reference, fill is estimated from texture and object detection, which is less precise.'}
                </small>
              </div>
            </div>
            <ul className="roi-reference-checklist">
              <li>The bin is completely empty</li>
              <li>Nobody is standing in front of the camera</li>
              <li>The camera is in its final position</li>
            </ul>
            <div className="roi-reference-actions">
              {reference.has_reference && (
                <button className="btn btn-secondary btn-sm" onClick={handleClearReference} disabled={refBusy}>
                  <Trash2 size={14} /> Clear
                </button>
              )}
              <button className="btn btn-primary btn-sm" onClick={handleCaptureReference} disabled={refBusy}>
                <Camera size={14} />
                {refBusy ? 'Working…' : reference.has_reference ? 'Recapture now' : 'Capture empty bin now'}
              </button>
            </div>
          </div>
        ) : (
          <div className="roi-shortcuts">
            <span><Crosshair size={12} /> Click to add</span>
            <span>Drag a point to move it</span>
            <span>Right-click a point to delete it</span>
            <span><kbd>Ctrl</kbd>+<kbd>Z</kbd> undo</span>
          </div>
        )}

        <div className="roi-footer">
          <div className="roi-footer-left">
            <button className="btn btn-secondary btn-sm" onClick={handleUndo} disabled={!history.length}>
              <Undo2 size={14} /> Undo
            </button>
            {editZone && (
              <button className="btn btn-secondary btn-sm" onClick={handleClear} disabled={!points[editZone].length}>
                <RotateCcw size={14} /> Clear {ZONES[editZone].label.toLowerCase()}
              </button>
            )}
          </div>
          <div className="roi-footer-right">
            <button className="btn btn-secondary btn-sm" onClick={requestClose}>Cancel</button>
            <button className="btn btn-primary btn-sm" onClick={handleSave} disabled={saving || !dirty}>
              <Save size={14} />
              {saving ? 'Saving…' : 'Save calibration'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default RoiModal;
