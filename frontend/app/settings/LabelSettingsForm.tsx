"use client";

import { useMemo, useState } from "react";

import type { LabelSetting } from "@/lib/clientSettings";

type Props = {
  initialLabels: LabelSetting[];
};

export default function LabelSettingsForm({ initialLabels }: Props) {
  const [labels, setLabels] = useState<LabelSetting[]>(initialLabels);
  const labelCount = labels.length;

  const canDelete = useMemo(() => labels.length > 1, [labels.length]);

  function addLabel() {
    const nextNumber = labels.length + 1;
    setLabels((current) => [
      ...current,
      {
        key: `custom-${Date.now()}`,
        name: `Nouveau libellé ${nextNumber}`,
        description: "Décrivez précisément les emails qui doivent recevoir ce libellé.",
        color: "#14b8a6",
        prepareDraft: false,
        autoReply: false,
        autoDelete: false,
        markAsRead: false,
        autoDeleteUnreadAfterDays: null,
        priority: 10,
      },
    ]);
  }

  function updateLabel(index: number, patch: Partial<LabelSetting>) {
    setLabels((current) => current.map((label, labelIndex) => (labelIndex === index ? { ...label, ...patch } : label)));
  }

  function deleteLabel(index: number) {
    if (!canDelete) return;
    setLabels((current) => current.filter((_, labelIndex) => labelIndex !== index));
  }

  return (
    <form action="/api/settings/labels" method="post" className="settings-panel">
      <input type="hidden" name="labelCount" value={labelCount} />
      <div className="settings-toolbar">
        <div>
          <p className="eyebrow">Réglages des libellés</p>
          <strong>Personnalisez les règles de tri</strong>
          <span>Ajoutez, modifiez ou supprimez vos libellés, puis enregistrez pour synchroniser Gmail.</span>
        </div>
        <div className="settings-toolbar-actions">
          <button type="button" className="secondary-settings-button" onClick={addLabel}>
            Ajouter un libellé
          </button>
          <button type="submit">Enregistrer les paramètres</button>
        </div>
      </div>

      <div className="settings-list">
        {labels.map((label, index) => (
          <details className="settings-row" key={label.key} open={index === 0}>
            <summary className="settings-row-summary">
              <span className="label-preview">
                <span className="label-color-dot" style={{ backgroundColor: label.color }} />
                <span>
                  <strong>{label.name || label.key}</strong>
                  <small>{label.description}</small>
                </span>
              </span>
              <span className="active-rules-count">
                {activeRulesCount(label)} action{activeRulesCount(label) > 1 ? "s" : ""} active{activeRulesCount(label) > 1 ? "s" : ""}
              </span>
            </summary>

            <div className="settings-row-body">
              <input type="hidden" name={`labels.${index}.key`} value={label.key} />
              <input type="hidden" name={`labels.${index}.priority`} value={label.priority || 10} />

              <label className="setting-field">
                Nom affiché
                <input
                  name={`labels.${index}.name`}
                  value={label.name}
                  maxLength={64}
                  required
                  onChange={(event) => updateLabel(index, { name: event.target.value })}
                />
              </label>

              <label className="setting-field color-field">
                Couleur
                <input
                  name={`labels.${index}.color`}
                  type="color"
                  value={label.color}
                  onChange={(event) => updateLabel(index, { color: event.target.value })}
                />
              </label>

              <label className="setting-field description-field">
                Description
                <textarea
                  name={`labels.${index}.description`}
                  value={label.description}
                  maxLength={360}
                  rows={2}
                  required
                  onChange={(event) => updateLabel(index, { description: event.target.value })}
                />
              </label>

              <div className="toggle-grid">
                <label>
                  <input
                    name={`labels.${index}.prepareDraft`}
                    type="checkbox"
                    checked={label.prepareDraft}
                    onChange={(event) => updateLabel(index, { prepareDraft: event.target.checked })}
                  />
                  Préparer un brouillon
                </label>
                <label>
                  <input
                    name={`labels.${index}.autoReply`}
                    type="checkbox"
                    checked={label.autoReply}
                    onChange={(event) => updateLabel(index, { autoReply: event.target.checked })}
                  />
                  Réponse auto
                </label>
                <label>
                  <input
                    name={`labels.${index}.autoDelete`}
                    type="checkbox"
                    checked={label.autoDelete}
                    onChange={(event) => updateLabel(index, { autoDelete: event.target.checked })}
                  />
                  Suppression auto
                </label>
                <label>
                  <input
                    name={`labels.${index}.markAsRead`}
                    type="checkbox"
                    checked={label.markAsRead}
                    onChange={(event) => updateLabel(index, { markAsRead: event.target.checked })}
                  />
                  Marquer comme lu
                </label>
              </div>

              <label className="setting-field unread-delay-field">
                Supprimer si le mail reste non lu aprÃ¨s
                <span>
                  <input
                    name={`labels.${index}.autoDeleteUnreadAfterDays`}
                    type="number"
                    min={1}
                    max={365}
                    placeholder="DÃ©sactivÃ©"
                    value={label.autoDeleteUnreadAfterDays || ""}
                    onChange={(event) =>
                      updateLabel(index, {
                        autoDeleteUnreadAfterDays: event.target.value ? Number(event.target.value) : null,
                      })
                    }
                  />
                  jours
                </span>
              </label>

              <div className="settings-row-controls">
                <button type="button" className="delete-label-button" disabled={!canDelete} onClick={() => deleteLabel(index)}>
                  Supprimer ce libellé
                </button>
              </div>
            </div>
          </details>
        ))}
      </div>

      <div className="settings-actions">
        <p>Les réponses et suppressions automatiques suivent uniquement les paramètres définis par vous.</p>
      </div>
    </form>
  );
}

function activeRulesCount(label: LabelSetting) {
  return Number(label.prepareDraft) + Number(label.autoReply) + Number(label.autoDelete) + Number(label.markAsRead) + Number(Boolean(label.autoDeleteUnreadAfterDays));
}
