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
// File: ui/src_ui/components/security/LockdownOverlay.tsx
// Author: Gabriel Moraes
// Date: 2026-09-03

import React, { useState, useRef, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { ShieldAlert, Lock, User, Eye, EyeOff, AlertOctagon, Loader2, KeyRound } from 'lucide-react';
import { useSecurityStore } from '../../stores';

export const LockdownOverlay: React.FC = () => {
  const { t } = useTranslation();
  const { isLockedDown, isAuthenticating, authError, submitUnlock } = useSecurityStore();

  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isLockedDown) {
      setUsername('');
      setPassword('');
      setTimeout(() => {
        inputRef.current?.focus();
      }, 100);
    }
  }, [isLockedDown]);

  if (!isLockedDown) return null;

  const handleUnlock = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username.trim() || !password) return;
    await submitUnlock(username.trim(), password);
  };

  return (
    <div className="fixed inset-0 z-[100] bg-red-950/98 backdrop-blur-xl flex flex-col items-center justify-center p-6 text-white select-none animate-in fade-in duration-300 overflow-y-auto">
      <div className="w-full max-w-lg flex flex-col items-center text-center space-y-6">
        {/* Animated Emergency Beacon */}
        <div className="relative">
          <div className="w-24 h-24 rounded-3xl bg-red-600/30 border-2 border-red-500/60 flex items-center justify-center animate-pulse shadow-2xl shadow-red-600/50">
            <ShieldAlert className="w-14 h-14 text-white drop-shadow-md" />
          </div>
          <div className="absolute -top-1 -right-1 w-6 h-6 rounded-full bg-red-500 flex items-center justify-center animate-ping">
            <AlertOctagon className="w-4 h-4 text-white" />
          </div>
        </div>

        {/* Title & Warning Notices */}
        <div className="space-y-2">
          <h1 className="text-2xl sm:text-3xl font-black tracking-tight text-white uppercase drop-shadow-lg">
            {t('security.lockdownTitle', 'SISTEMA BLOQUEADO (LOCKDOWN)')}
          </h1>
          <p className="text-sm font-medium text-red-200 max-w-md mx-auto leading-relaxed">
            {t(
              'security.lockdownDesc1',
              'Múltiplas tentativas de acesso inválidas. A infraestrutura física e os motores de IA foram isolados para proteção.'
            )}
          </p>
          <p className="text-xs text-red-300/80 font-mono">
            {t(
              'security.lockdownDesc2',
              'Apenas um Super Usuário ou a Chave Mestra podem reestabelecer o funcionamento.'
            )}
          </p>
        </div>

        {/* Form Container */}
        <div className="w-full max-w-sm bg-black/40 border border-red-500/40 rounded-2xl p-6 shadow-2xl backdrop-blur-md space-y-4 text-left">
          {/* Error Message */}
          {authError && (
            <div className="p-3 rounded-xl bg-amber-500/20 border border-amber-500/40 text-amber-200 text-xs flex items-center gap-2">
              <AlertOctagon className="w-4 h-4 shrink-0 text-amber-400" />
              <span>{authError}</span>
            </div>
          )}

          <form onSubmit={handleUnlock} className="space-y-3.5">
            <div className="space-y-1">
              <label className="text-xs font-bold text-red-200 uppercase tracking-wider">
                {t('security.superuser', 'Super Usuário / Usuário')}
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-red-300">
                  <User className="w-4 h-4" />
                </div>
                <input
                  ref={inputRef}
                  type="text"
                  disabled={isAuthenticating}
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="admin"
                  className="w-full pl-9 pr-3 py-2.5 text-xs rounded-xl bg-red-950/60 border border-red-500/40 focus:border-white focus:ring-1 focus:ring-white outline-none text-white placeholder:text-red-400/50"
                  required
                />
              </div>
            </div>

            <div className="space-y-1">
              <label className="text-xs font-bold text-red-200 uppercase tracking-wider">
                {t('security.password', 'Senha')}
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-red-300">
                  <Lock className="w-4 h-4" />
                </div>
                <input
                  type={showPassword ? 'text' : 'password'}
                  disabled={isAuthenticating}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••••••"
                  className="w-full pl-9 pr-10 py-2.5 text-xs rounded-xl bg-red-950/60 border border-red-500/40 focus:border-white focus:ring-1 focus:ring-white outline-none text-white placeholder:text-red-400/50"
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute inset-y-0 right-0 pr-3 flex items-center text-red-300 hover:text-white"
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={isAuthenticating || !username.trim() || !password}
              className="w-full py-3 px-4 rounded-xl text-xs font-bold bg-white text-red-950 hover:bg-red-50 shadow-lg shadow-black/50 transition-all flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed transform active:scale-98"
            >
              {isAuthenticating ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin text-red-900" />
                  <span>{t('security.verifyingSuperuser', 'Verificando Superusuário...')}</span>
                </>
              ) : (
                <>
                  <KeyRound className="w-4 h-4 text-red-900" />
                  <span>{t('security.unlockSystem', 'DESBLOQUEAR SISTEMA')}</span>
                </>
              )}
            </button>
          </form>
        </div>

        {/* Security badge footer */}
        <div className="flex items-center gap-2 text-[11px] text-red-300/60">
          <span>SYNAPSE Active Perimeter Defense</span>
          <span>•</span>
          <span>Lockdown Engine v2.0</span>
        </div>
      </div>
    </div>
  );
};
