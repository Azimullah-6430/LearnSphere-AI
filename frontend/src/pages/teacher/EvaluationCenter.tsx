import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import Header from '../../components/Header';
import Sidebar from '../../components/Sidebar';
import { teacherService } from '../../services/apiService';
import { CheckCircle, Clock, AlertCircle } from 'lucide-react';
import toast from 'react-hot-toast';

interface Submission {
  id: string;
  student_name: string;
  student_email: string;
  subject: string;
  level: string;
  stream: string;
  created_at: string;
  status: string;
}

const EvaluationCenter: React.FC = () => {
  const [submissions, setSubmissions] = useState<Submission[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all');
  const navigate = useNavigate();

  useEffect(() => {
    fetchSubmissions();
  }, []);

  const fetchSubmissions = async () => {
    try {
      setLoading(true);
      const data = await teacherService.getPendingSubmissions();
      setSubmissions(data.submissions || []);
    } catch (error) {
      toast.error('Failed to load submissions');
    } finally {
      setLoading(false);
    }
  };

  const filteredSubmissions = submissions.filter(sub => {
    if (filter === 'pending') return sub.status === 'pending';
    if (filter === 'evaluated') return sub.status === 'evaluated';
    return true;
  });

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'pending':
        return <span className="px-3 py-1 bg-yellow-100 text-yellow-800 rounded-full text-sm">Pending AI Evaluation</span>;
      case 'evaluated':
        return <span className="px-3 py-1 bg-green-100 text-green-800 rounded-full text-sm">Evaluated</span>;
      case 'flagged':
        return <span className="px-3 py-1 bg-red-100 text-red-800 rounded-full text-sm">Plagiarism Flagged</span>;
      default:
        return <span className="px-3 py-1 bg-gray-100 text-gray-800 rounded-full text-sm">{status}</span>;
    }
  };

  if (loading) {
    return (
      <div className="flex h-screen bg-gray-100">
        <Sidebar />
        <div className="flex-1 flex flex-col">
          <Header />
          <main className="flex-1 flex items-center justify-center">
            <div className="text-2xl font-bold text-gray-600">Loading submissions...</div>
          </main>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen bg-gray-100">
      <Sidebar />
      <div className="flex-1 flex flex-col">
        <Header />
        <main className="flex-1 overflow-auto p-8">
          <div className="max-w-7xl mx-auto">
            <div className="flex justify-between items-center mb-8">
              <h1 className="text-3xl font-bold">📝 Evaluation Center</h1>
              <button
                onClick={fetchSubmissions}
                className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg transition"
              >
                ↻ Refresh
              </button>
            </div>

            {/* Statistics */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
              <div className="bg-white rounded-lg shadow p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-gray-600 text-sm">Total Submissions</p>
                    <p className="text-3xl font-bold text-blue-600 mt-2">{submissions.length}</p>
                  </div>
                  <Clock className="text-blue-400" size={40} />
                </div>
              </div>
              <div className="bg-white rounded-lg shadow p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-gray-600 text-sm">Pending AI Evaluation</p>
                    <p className="text-3xl font-bold text-yellow-600 mt-2">
                      {submissions.filter(s => s.status === 'pending').length}
                    </p>
                  </div>
                  <AlertCircle className="text-yellow-400" size={40} />
                </div>
              </div>
              <div className="bg-white rounded-lg shadow p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-gray-600 text-sm">Teacher Evaluated</p>
                    <p className="text-3xl font-bold text-green-600 mt-2">
                      {submissions.filter(s => s.status === 'evaluated').length}
                    </p>
                  </div>
                  <CheckCircle className="text-green-400" size={40} />
                </div>
              </div>
            </div>

            {/* Filters */}
            <div className="mb-6 flex gap-2">
              <button
                onClick={() => setFilter('all')}
                className={`px-4 py-2 rounded-lg transition ${
                  filter === 'all' ? 'bg-blue-600 text-white' : 'bg-white text-gray-700 border'
                }`}
              >
                All Submissions
              </button>
              <button
                onClick={() => setFilter('pending')}
                className={`px-4 py-2 rounded-lg transition ${
                  filter === 'pending' ? 'bg-blue-600 text-white' : 'bg-white text-gray-700 border'
                }`}
              >
                Pending
              </button>
              <button
                onClick={() => setFilter('evaluated')}
                className={`px-4 py-2 rounded-lg transition ${
                  filter === 'evaluated' ? 'bg-blue-600 text-white' : 'bg-white text-gray-700 border'
                }`}
              >
                Evaluated
              </button>
            </div>

            {/* Submissions Table */}
            <div className="bg-white rounded-lg shadow overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full">
                  <thead className="bg-gray-100 border-b">
                    <tr>
                      <th className="px-6 py-4 text-left font-semibold text-gray-700">Student</th>
                      <th className="px-6 py-4 text-left font-semibold text-gray-700">Subject</th>
                      <th className="px-6 py-4 text-left font-semibold text-gray-700">Level</th>
                      <th className="px-6 py-4 text-left font-semibold text-gray-700">Status</th>
                      <th className="px-6 py-4 text-left font-semibold text-gray-700">Submitted</th>
                      <th className="px-6 py-4 text-left font-semibold text-gray-700">Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredSubmissions.length > 0 ? (
                      filteredSubmissions.map((submission) => (
                        <tr key={submission.id} className="border-b hover:bg-gray-50 transition">
                          <td className="px-6 py-4">
                            <div>
                              <p className="font-medium text-gray-900">{submission.student_name}</p>
                              <p className="text-sm text-gray-600">{submission.student_email}</p>
                            </div>
                          </td>
                          <td className="px-6 py-4 text-gray-700">{submission.subject}</td>
                          <td className="px-6 py-4 text-gray-700">{submission.level}</td>
                          <td className="px-6 py-4">{getStatusBadge(submission.status)}</td>
                          <td className="px-6 py-4 text-sm text-gray-600">
                            {new Date(submission.created_at).toLocaleDateString()}
                          </td>
                          <td className="px-6 py-4">
                            <button
                              onClick={() => navigate(`/teacher/evaluations/${submission.id}`)}
                              className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg text-sm transition"
                            >
                              Review & Evaluate
                            </button>
                          </td>
                        </tr>
                      ))
                    ) : (
                      <tr>
                        <td colSpan={6} className="px-6 py-8 text-center text-gray-500">
                          No submissions found
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
};

export default EvaluationCenter;