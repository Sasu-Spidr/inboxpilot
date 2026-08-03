"use client";

import { useState } from "react";

import type { LabelSetting } from "@/lib/clientSettings";

type Props = {
  initialLabels: LabelSetting[];
};

export default function LabelSettingsForm({ initialLabels }: Props) {
  const [labels, setLabels] = useState<LabelSetting[]>(initialLabels);
  const labelCount = labels.length;

  function updateLabel(index: number, patch: Partial<LabelSetting>) {
    setLabels((current) => current.map((label, labelIndex) => (labelIndex === index ? { ...label, ...patch } : label)));
  }

  return (
    <form action="/api/settings/labels" method="post" className="settings-panel">
      <input type="hidden" name="labelCount" value={labelCount} />
      <div className="settings-toolbar">
        <div>
          <p className="eyebrow">Réglages des libellés</p>
          <strong>Les cinq libellés par défaut</strong>
          <span>Les libellés sont fixes. Vous pouvez seulement ajuster leurs règles, couleurs et descriptions.</span>
        </div>
        <div className="settings-toolbar-actions">
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
                {activeRulesCount(label)} règle{activeRulesCount(label) > 1 ? "s" : ""} active{activeRulesCount(label) > 1 ? "s" : ""}
              </span>
            </summary>

            <div className="settings-row-body">
              <input type="hidden" name={`labels.${index}.key`} value={label.key} />
              <input type="hidden" name={`labels.${index}.name`} value={label.name} />
              <input type="hidden" name={`labels.${index}.priority`} value={label.priority || 10} />

              <div className="setting-field">
                <span>Nom affiché</span>
                <strong>{label.name}</strong>
              </div>

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
              </div>

              <label className="setting-field unread-delay-field">
                Supprimer si le mail reste non lu après
                <span>
                  <input
                    name={`labels.${index}.autoDeleteUnreadAfterDays`}
                    type="number"
                    min={1}
                    max={365}
                    placeholder="Désactivé"
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
  return Number(label.prepareDraft) + Number(label.autoReply) + Number(label.autoDelete) + Number(Boolean(label.autoDeleteUnreadAfterDays));
}
