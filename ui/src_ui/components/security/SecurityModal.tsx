// SYNAPSE - A Gateway of Intelligent Perception for Traffic Management
// Copyright (C) 2026 Noxfort Systems
//
// This program is free software: you can redistribute it and/or modify
// it under the terms of the GNU Affero General Public License as
// published by the Free Software Foundation, either version 3 of the
// License, or (at your option) any later version.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU Affero General Public License for more details.
//
// You should have received a copy of the GNU Affero General Public License
// along with this program.  If not, see <https://www.gnu.org/licenses/>.
//
// File: ui/src_ui/components/security/SecurityModal.tsx
// Author: Gabriel Moraes
// Date: 2026-09-03

import React, { useState, useEffect, useRef } from 'react';
import { useTranslation } from 'react-i18next';
import { ShieldCheck, Lock, User, Eye, EyeOff, AlertTriangle, Loader2 } from 'lucide-react';
import { useSecurityStore } from '../../stores';

export const SecurityModal: React.FC = () => {
  const { t } = useTranslation();
  const {
    isAuthModalOpen,
    isAuthenticating,
    authError,
    cancelAuth,
    submitAuth,
  } = useSecurityStore();

  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const usernameInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isAuthModalOpen) {
      setUsername('');
      setPassword('');
      setShowPassword(false);
      setTimeout(() => {
        usernameInputRef.current?.focus();
      }, 50);
    }
  }, [isAuthModalOpen]);

  if (!isAuthModalOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username.trim() || !password) return;
    await submitAuth(username.trim(), password);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-md p-4 animate-in fade-in select-none">
      <div className="w-full max-w-md glass-panel bg-surface p-6 rounded-2xl shadow-2xl border border-border space-y-5">
        {/* Header */}
        <div className="flex items-center gap-3 border-b border-border/80 pb-4">
          <div className="w-10 h-10 rounded-xl bg-primary-500/10 border border-primary-500/20 flex items-center justify-center text-primary-500 dark:text-primary-400 shrink-0">
            <ShieldCheck className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-base font-bold text-slate-900 dark:text-white tracking-tight">
              {t('security.authRequired', 'Autenticação Necessária')}
            </h2>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              {t('security.authPrompt', 'Ação restrita. Insira suas credenciais para prosseguir.')}
            </p>
          </div>
        </div>

        {/* Error Feedback */}
        {authError && (
          <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-600 dark:text-rose-400 text-xs flex items-center gap-2 animate-shake">
            <AlertTriangle className="w-4 h-4 shrink-0" />
            <span>{authError}</span>
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-slate-700 dark:text-slate-300">
              {t('security.username', 'Nome de Usuário')}
            </label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                <User className="w-4 h-4" />
              </div>
              <input
                ref={usernameInputRef}
                type="text"
                disabled={isAuthenticating}
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder={t('security.usernamePlaceholder', 'ex.: admin...')}
                className="w-full pl-9 pr-3 py-2 text-xs rounded-xl bg-background border border-border focus:border-primary-500 focus:ring-1 focus:ring-primary-500 outline-none transition-all text-slate-900 dark:text-white"
                required
              />
            </div>
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-slate-700 dark:text-slate-300">
              {t('security.password', 'Senha')}
            </label>
            <div className="relative">
              <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                <Lock className="w-4 h-4" />
              </div>
              <input
                type={showPassword ? 'text' : 'password'}
                disabled={isAuthenticating}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••••••"
                className="w-full pl-9 pr-10 py-2 text-xs rounded-xl bg-background border border-border focus:border-primary-500 focus:ring-1 focus:ring-primary-500 outline-none transition-all text-slate-900 dark:text-white"
                required
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute inset-y-0 right-0 pr-3 flex items-center text-slate-400 hover:text-slate-200"
              >
                {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex items-center justify-end gap-2.5 pt-2 border-t border-border/80">
            <button
              type="button"
              onClick={cancelAuth}
              disabled={isAuthenticating}
              className="px-4 py-2 rounded-xl text-xs font-semibold text-slate-600 dark:text-slate-400 hover:bg-surfaceHover hover:text-slate-900 dark:hover:text-white transition-all"
            >
              {t('common.cancel', 'Cancelar')}
            </button>
            <button
              type="submit"
              disabled={isAuthenticating || !username.trim() || !password}
              className="px-5 py-2 rounded-xl text-xs font-bold bg-primary-600 hover:bg-primary-500 text-white shadow-md shadow-primary-600/20 transition-all flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isAuthenticating ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  <span>{t('security.authenticating', 'Autenticando...')}</span>
                </>
              ) : (
                <span>{t('security.authenticate', 'Autenticar')}</span>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
