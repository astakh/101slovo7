import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft, Search, ChevronLeft, ChevronRight, Loader2, AlertCircle, Shield } from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { useDbTables, useDbTableContent } from '../hooks/useApi';
import { Button } from '../components/ui/Button';
import { Card, CardContent } from '../components/ui/Card';
import { cn } from '../lib/utils';

export default function AdminDb() {
  const navigate = useNavigate();
  const { user } = useAuth();

  const [selectedTable, setSelectedTable] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(25);
  const [search, setSearch] = useState('');
  const [appliedSearch, setAppliedSearch] = useState('');
  const [orderBy, setOrderBy] = useState<string | null>(null);
  const [orderDir, setOrderDir] = useState<'asc' | 'desc'>('asc');

  const { data: tables, isLoading: loadingTables, error: tablesError } = useDbTables();

  const { data: tableContent, isLoading: loadingContent, error: contentError } = useDbTableContent(
    selectedTable,
    { page, pageSize, search: appliedSearch, orderBy, orderDir }
  );

  if (!user?.is_admin) {
    navigate('/dashboard');
    return null;
  }

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setAppliedSearch(search);
    setPage(1);
  };

  const handleClearSearch = () => {
    setSearch('');
    setAppliedSearch('');
    setPage(1);
  };

  const handleSort = (columnName: string) => {
    if (orderBy === columnName) {
      setOrderDir(orderDir === 'asc' ? 'desc' : 'asc');
    } else {
      setOrderBy(columnName);
      setOrderDir('asc');
    }
    setPage(1);
  };

  const totalPages = tableContent?.total ? Math.ceil(tableContent.total / pageSize) : 1;

  const renderPaginationButtons = () => {
    const buttons: number[] = [];
    if (totalPages <= 5) {
      for (let i = 1; i <= totalPages; i++) buttons.push(i);
    } else if (page <= 3) {
      for (let i = 1; i <= 5; i++) buttons.push(i);
    } else if (page >= totalPages - 2) {
      for (let i = totalPages - 4; i <= totalPages; i++) buttons.push(i);
    } else {
      for (let i = page - 2; i <= page + 2; i++) buttons.push(i);
    }
    return buttons;
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-50 via-white to-purple-50">
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex items-center justify-between h-16">
          <Button variant="ghost" onClick={() => navigate('/admin')}>
            <ArrowLeft size={20} /> Админ
          </Button>
          <h1 className="text-lg font-bold text-gray-900 flex items-center gap-2">
            <Shield size={20} /> База данных
          </h1>
          <div className="w-20" />
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="flex gap-6">
          <Card className="w-64 flex-shrink-0 h-fit">
            <CardContent className="p-4">
              <h3 className="font-semibold text-gray-900 mb-3">Таблицы</h3>
              {loadingTables && <Loader2 className="animate-spin text-indigo-600" size={24} />}
              {tablesError && <p className="text-sm text-red-600">Ошибка загрузки</p>}
              {tables && (
                <div className="space-y-1">
                  {tables.map((t) => (
                    <button
                      key={t.table_name}
                      onClick={() => { setSelectedTable(t.table_name); setPage(1); setOrderBy(null); setAppliedSearch(''); setSearch(''); }}
                      className={cn(
                        'w-full text-left px-3 py-2 rounded-lg text-sm transition-colors font-mono',
                        selectedTable === t.table_name
                          ? 'bg-indigo-100 text-indigo-900 font-semibold'
                          : 'text-gray-700 hover:bg-gray-100'
                      )}
                    >
                      {t.table_name}
                    </button>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          <div className="flex-1 min-w-0">
            {!selectedTable ? (
              <Card>
                <CardContent className="p-12 text-center text-gray-500">
                  Выберите таблицу из списка слева
                </CardContent>
              </Card>
            ) : (
              <Card>
                <CardContent className="p-6">
                  <div className="flex items-center justify-between mb-4">
                    <div>
                      <h2 className="text-2xl font-bold text-gray-900 font-mono">{tableContent?.table_name || selectedTable}</h2>
                      <p className="text-sm text-gray-500 mt-1">
                        {tableContent?.total !== null && tableContent?.total !== undefined
                          ? `Всего строк: ${tableContent.total}`
                          : 'Страница загружена'}
                        {' • '}{tableContent?.columns?.length ?? 0} колонок
                      </p>
                    </div>
                  </div>

                  <form onSubmit={handleSearch} className="mb-4 flex gap-2">
                    <div className="relative flex-1">
                      <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={18} />
                      <input
                        type="text"
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                        placeholder="Поиск по текстовым колонкам..."
                        className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 focus:border-transparent outline-none"
                      />
                    </div>
                    <Button type="submit">
                      <Search size={18} /> Искать
                    </Button>
                    {appliedSearch && (
                      <Button type="button" variant="secondary" onClick={handleClearSearch}>
                        Сбросить
                      </Button>
                    )}
                  </form>

                  {appliedSearch && (
                    <div className="mb-4 px-3 py-2 bg-purple-50 border border-purple-200 rounded-lg text-sm text-purple-800">
                      🔍 Поиск: <span className="font-mono font-semibold">"{appliedSearch}"</span>
                    </div>
                  )}

                  <div className="flex items-center gap-2 mb-4 text-sm">
                    <span className="text-gray-600">Строк на странице:</span>
                    <select
                      value={pageSize}
                      onChange={(e) => { setPageSize(Number(e.target.value)); setPage(1); }}
                      className="border border-gray-300 rounded px-2 py-1"
                    >
                      <option value={10}>10</option>
                      <option value={25}>25</option>
                      <option value={50}>50</option>
                      <option value={100}>100</option>
                    </select>
                  </div>

                  {loadingContent && (
                    <div className="flex items-center justify-center py-12">
                      <Loader2 className="animate-spin text-indigo-600" size={32} />
                    </div>
                  )}

                  {contentError && (
                    <div className="flex items-center gap-2 text-red-600 py-4">
                      <AlertCircle size={20} />
                      <span>{(contentError as Error).message}</span>
                    </div>
                  )}

                  {tableContent && !loadingContent && (
                    <>
                      <div className="overflow-x-auto">
                        <table className="w-full text-sm">
                          <thead>
                            <tr className="border-b border-gray-200">
                              {tableContent.columns.map((col) => (
                                <th
                                  key={col.name}
                                  onClick={() => handleSort(col.name)}
                                  className="px-3 py-2 text-left font-semibold text-gray-700 cursor-pointer hover:bg-gray-50 whitespace-nowrap"
                                >
                                  {col.name}
                                  {orderBy === col.name && (
                                    <span className="ml-1">{orderDir === 'asc' ? '↑' : '↓'}</span>
                                  )}
                                </th>
                              ))}
                            </tr>
                          </thead>
                          <tbody>
                            {tableContent.rows.map((row, rowIdx) => (
                              <tr key={rowIdx} className="border-b border-gray-100 hover:bg-gray-50">
                                {tableContent.columns.map((col) => (
                                  <td key={col.name} className="px-3 py-2 text-gray-700 max-w-xs truncate font-mono text-xs">
                                    {String(row[col.name] ?? '')}
                                  </td>
                                ))}
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>

                      {tableContent.total !== null && totalPages > 1 && (
                        <div className="flex items-center justify-between mt-4 pt-4 border-t border-gray-200">
                          <div className="text-sm text-gray-600">
                            Страница {page} из {totalPages} ({tableContent.rows.length} строк на странице)
                          </div>
                          <div className="flex items-center gap-2">
                            <Button variant="secondary" size="default" onClick={() => setPage(1)} disabled={page === 1}>
                              ««
                            </Button>
                            <Button variant="secondary" size="default" onClick={() => setPage(Math.max(1, page - 1))} disabled={page === 1}>
                              <ChevronLeft size={16} /> Назад
                            </Button>
                            <div className="flex gap-1">
                              {renderPaginationButtons().map((pageNum) => (
                                <button
                                  key={pageNum}
                                  onClick={() => setPage(pageNum)}
                                  className={cn(
                                    'w-8 h-8 rounded text-sm font-medium transition-colors',
                                    page === pageNum
                                      ? 'bg-purple-600 text-white'
                                      : 'border border-gray-300 hover:bg-gray-50'
                                  )}
                                >
                                  {pageNum}
                                </button>
                              ))}
                            </div>
                            <Button variant="secondary" size="default" onClick={() => setPage(Math.min(totalPages, page + 1))} disabled={page === totalPages}>
                              Вперёд <ChevronRight size={16} />
                            </Button>
                            <Button variant="secondary" size="default" onClick={() => setPage(totalPages)} disabled={page === totalPages}>
                              »»
                            </Button>
                          </div>
                        </div>
                      )}
                    </>
                  )}
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}