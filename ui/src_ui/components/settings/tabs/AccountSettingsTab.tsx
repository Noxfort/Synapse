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
// File: ui/src_ui/components/settings/tabs/AccountSettingsTab.tsx
// Author: Gabriel Moraes
// Date: 2026-09-03

import React, { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import {
  UserPlus,
  Trash2,
  RefreshCw,
  Shield,
  User,
  CheckCircle2,
  AlertTriangle,
  Loader2,
  Lock,
} from 'lucide-react';
import { useSecurityStore } from '../../../stores';
import { UserAccount } from '../../../services/api';

export const AccountSettingsTab: React.FC = () => {
  const { t } = useTranslation();
  const {
    registeredUsers,
    isLoadingUsers,
    fetchUsers,
    addUser,
    removeUser,
  } = useSecurityStore();

  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState<'OPERATOR' | 'SUPERUSER'>('OPERATOR');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [feedback, setFeedback] = useState<{ type: 'success' | 'error'; message: string } | null>(null);

  useEffect(() => {
    fetchUsers();
  }, [fetchUsers]);

  const handleAddUser = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username.trim() || !password) return;

    setIsSubmitting(true);
    setFeedback(null);

    const success = await addUser(username.trim(), password, role);
    setIsSubmitting(false);

    if (success) {
      setFeedback({
        type: 'success',
        message: `Usuário '${username.trim()}' adicionado com sucesso (${role}).`,
      });
      setUsername('');
      setPassword('');
      setRole('OPERATOR');
    } else {
      setFeedback({
        type: 'error',
        message: 'Falha ao adicionar usuário. Verifique se o usuário já existe.',
      });
    }
  };

  const handleRemoveUser = async (targetUser: string) => {
    if (targetUser === 'admin') return;
    if (!window.confirm(`Tem certeza que deseja remover o usuário '${targetUser}'?`)) return;

    setFeedback(null);
    const success = await removeUser(targetUser);
    if (success) {
      setFeedback({
        type: 'success',
        message: `Usuário '${targetUser}' removido com sucesso.`,
      });
    } else {
      setFeedback({
        type: 'error',
        message: `Erro ao remover usuário '${targetUser}'.`,
      });
    }
  };

  return (
    <div className="space-y-6 text-xs select-none">
      {/* Feedback Banner */}
      {feedback && (
        <div
          className={`p-3 rounded-xl border flex items-center justify-between gap-2 animate-in fade-in ${
            feedback.type === 'success'
              ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-600 dark:text-emerald-400'
              : 'bg-rose-500/10 border-rose-500/20 text-rose-600 dark:text-rose-400'
          }`}
        >
          <div className="flex items-center gap-2">
            {feedback.type === 'success' ? (
              <CheckCircle2 className="w-4 h-4 shrink-0" />
            ) : (
              <AlertTriangle className="w-4 h-4 shrink-0" />
            )}
            <span className="font-medium">{feedback.message}</span>
          </div>
          <button
            onClick={() => setFeedback(null)}
            className="text-[10px] uppercase font-bold opacity-60 hover:opacity-100"
          >
            Fechar
          </button>
        </div>
      )}

      {/* Add User Section */}
      <div className="p-4 rounded-xl bg-surfaceElevated border border-border space-y-4">
        <h3 className="font-bold text-slate-900 dark:text-white flex items-center gap-2">
          <UserPlus className="w-4 h-4 text-primary-500" />
          <span>{t('accounts.addNewAccount', 'Adicionar Nova Conta:')}</span>
        </h3>

        <form onSubmit={handleAddUser} className="space-y-3">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            <div className="space-y-1">
              <label className="text-[11px] font-semibold text-slate-700 dark:text-slate-300">
                {t('security.username', 'Nome de Usuário')}
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-2.5 flex items-center pointer-events-none text-slate-400">
                  <User className="w-3.5 h-3.5" />
                </div>
                <input
                  type="text"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="ex.: operador_turno1"
                  className="w-full pl-8 pr-3 py-1.5 text-xs rounded-lg bg-background border border-border focus:border-primary-500 outline-none text-slate-900 dark:text-white"
                  required
                />
              </div>
            </div>

            <div className="space-y-1">
              <label className="text-[11px] font-semibold text-slate-700 dark:text-slate-300">
                {t('security.password', 'Senha')}
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-2.5 flex items-center pointer-events-none text-slate-400">
                  <Lock className="w-3.5 h-3.5" />
                </div>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••••••"
                  className="w-full pl-8 pr-3 py-1.5 text-xs rounded-lg bg-background border border-border focus:border-primary-500 outline-none text-slate-900 dark:text-white"
                  required
                />
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 items-end">
            <div className="space-y-1">
              <label className="text-[11px] font-semibold text-slate-700 dark:text-slate-300">
                {t('accounts.accessLevel', 'Nível de Acesso')}
              </label>
              <select
                value={role}
                onChange={(e) => setRole(e.target.value as 'OPERATOR' | 'SUPERUSER')}
                className="w-full px-3 py-1.5 text-xs rounded-lg bg-background border border-border focus:border-primary-500 outline-none text-slate-900 dark:text-white cursor-pointer"
              >
                <option value="OPERATOR">
                  {t('accounts.operator', 'Operador (Acesso Padrão)')}
                </option>
                <option value="SUPERUSER">
                  {t('accounts.superuser', 'Super Usuário (Acesso Total)')}
                </option>
              </select>
            </div>

            <button
              type="submit"
              disabled={isSubmitting || !username.trim() || !password}
              className="w-full py-2 px-4 rounded-lg text-xs font-bold bg-primary-600 hover:bg-primary-500 text-white shadow-md shadow-primary-600/20 transition-all flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isSubmitting ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <UserPlus className="w-3.5 h-3.5" />
              )}
              <span>{t('accounts.addUser', 'Adicionar Usuário')}</span>
            </button>
          </div>
        </form>
      </div>

      {/* Registered Accounts List */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h3 className="font-bold text-slate-900 dark:text-white flex items-center gap-2">
            <Shield className="w-4 h-4 text-accent-cyan" />
            <span>
              {t('accounts.registeredAccounts', 'Contas Cadastradas:')} ({registeredUsers.length})
            </span>
          </h3>

          <button
            onClick={() => fetchUsers()}
            disabled={isLoadingUsers}
            title={t('accounts.refreshList', 'Atualizar Lista')}
            className="p-1.5 rounded-lg text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white hover:bg-surfaceHover transition-colors"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isLoadingUsers ? 'animate-spin' : ''}`} />
          </button>
        </div>

        <div className="border border-border rounded-xl bg-background/50 divide-y divide-border/60 max-h-56 overflow-y-auto">
          {registeredUsers.length === 0 ? (
            <div className="p-4 text-center text-slate-400">
              {isLoadingUsers ? 'Carregando contas...' : 'Nenhuma conta cadastrada.'}
            </div>
          ) : (
            registeredUsers.map((user: UserAccount) => {
              const isSuper = user.role === 'SUPERUSER';
              return (
                <div
                  key={user.username}
                  className="p-3 flex items-center justify-between hover:bg-surfaceHover/50 transition-colors"
                >
                  <div className="flex items-center gap-2.5">
                    <div
                      className={`w-7 h-7 rounded-lg flex items-center justify-center ${
                        isSuper
                          ? 'bg-amber-500/10 text-amber-500 border border-amber-500/20'
                          : 'bg-primary-500/10 text-primary-500 border border-primary-500/20'
                      }`}
                    >
                      {isSuper ? <Shield className="w-3.5 h-3.5" /> : <User className="w-3.5 h-3.5" />}
                    </div>
                    <div>
                      <span className="font-bold text-slate-900 dark:text-white">
                        {user.username}
                      </span>
                    </div>
                  </div>

                  <div className="flex items-center gap-3">
                    <span
                      className={`px-2 py-0.5 rounded-full text-[10px] font-bold border ${
                        isSuper
                          ? 'bg-amber-500/15 text-amber-600 dark:text-amber-400 border-amber-500/30'
                          : 'bg-primary-500/15 text-primary-600 dark:text-primary-400 border-primary-500/30'
                      }`}
                    >
                      {user.role}
                    </span>

                    <button
                      onClick={() => handleRemoveUser(user.username)}
                      title={`Remover ${user.username}`}
                      className="p-1 rounded text-slate-400 hover:text-rose-500 hover:bg-rose-500/10 transition-colors"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
};
