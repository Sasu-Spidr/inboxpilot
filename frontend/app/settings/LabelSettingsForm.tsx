"use client";

import { useMemo, useState } from "react";

import type { LabelSetting } from "@/lib/clientSettings";
import { ALLOWED_LABELS } from "@/lib/labelAliases";

type Props = {
  initialLabels: LabelSetting[];
  selectedProvider?: "gmail" | "hotmail";
  selectedAccount?: string;
  selectedMailboxLabel: string;
};

const DEFAULT_LABEL_KEYS = new Set<string>(ALLOWED_LABELS);

export default function LabelSettingsForm({ initialLabels, selectedProvider, selectedAccount, selectedMailboxLabel }: Props) {
  const [labels, setLabels] = useState<LabelSetting[]>(initialLabels);
  const labelCount = labels.length;
  const defaultName = useMemo(() => nextCustomLabelName(labels), [labels]);

  function updateLabel(index: number, patch: Partial<LabelSetting>) {
    setLabels((current) => current.map((label, labelIndex) => (labelIndex === index ? { ...label, ...patch } : label)));
  }

  function addLabel() {
    const name = defaultName;
    setLabels((current) => [
      ...current,
      {
        key: name,
        name,
        description: "Décrivez précisément les emails qui doivent recevoir ce libellé.",
        color: "#14b8a6",
        priority: 20,
        prepareDraft: false,
        autoReply: false,
        autoDelete: false,
        markAsRead: false,
        autoDeleteUnreadAfterDays: null,
      },
    ]);
  }

  function removeLabel(index: number) {
    setLabels((current) => current.filter((_, labelIndex) => labelIndex !== index));
  }

  return (
    <form action="/api/settings/labels" method="post" className="settings-panel">
      <input type="hidden" name="labelCount" value={labelCount} />
      <input type="hidden" name="provider" value={selectedProvider || ""} />
      <input type="hidden" name="account" value={selectedAccount || ""} />
      <div className="settings-toolbar">
        <div>
          <p className="eyebrow">Réglages des libellés</p>
          <strong>Règles de tri pour {selectedMailboxLabel}</strong>
          <span>Ajoutez, modifiez ou supprimez les libellés de cette boîte, puis enregistrez pour synchroniser Gmail ou Outlook.</span>
        </div>
        <div className="settings-toolbar-actions">
          <button type="button" className="secondary-settings-button" onClick={addLabel}>
            Ajouter un libellé
          </button>
          <button type="submit">Enregistrer les paramètres</button>
        </div>
      </div>

      <div className="settings-list">
        {labels.map((label, index) => {
          const isDefault = DEFAULT_LABEL_KEYS.has(label.key);
          return (
            <details className="settings-row" key={`${label.key}:${index}`} open={index === 0}>
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

                <label className="setting-field">
                  Nom affiché
                  {isDefault ? (
                    <strong>{label.name}</strong>
                  ) : (
                    <input
                      type="text"
                      value={label.name}
                      maxLength={80}
                      required
                      onChange={(event) => {
                        const name = event.target.value;
                        updateLabel(index, { key: name, name });
                      }}
                    />
                  )}
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
                    maxLength={2000}
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

                {!isDefault && (
                  <button type="button" className="danger-settings-button" onClick={() => removeLabel(index)}>
                    Supprimer ce libellé
                  </button>
                )}
              </div>
            </details>
          );
        })}
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

function nextCustomLabelName(labels: LabelSetting[]) {
  const existing = new Set(labels.map((label) => label.name));
  let index = 1;
  while (existing.has(index === 1 ? "Nouveau libellé" : `Nouveau libellé ${index}`)) index += 1;
  return index === 1 ? "Nouveau libellé" : `Nouveau libellé ${index}`;
}
