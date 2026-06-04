import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import Header from '../../components/Header';
import Sidebar from '../../components/Sidebar';
import { teacherService } from '../../services/apiService';
import { Users, BookOpen, TrendingUp, AlertCircle, BarChart3, Settings } from 'lucide-react';
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import toast from 'react-hot-toast';

interface DashboardStats {
  total_students: number;
  total_submissions: number;
  pending_evaluations: number;
  plagiarism_flags: number;
  average_score: number;
  class_performance: any[];
  recent_submissions: any[];
}

const TeacherDashboard: React.FC = () => {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    fetchDashboardStats();
  }, []);

  const fetchDashboardStats = async () => {
    try {
      setLoading(true);
      const data = await teacherService.getDashboardStats();
      setStats(data);
    } catch (error) {
      toast.error('Failed to load dashboard statistics');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex h-screen bg-gray-100">
        <Sidebar />
        <div className="flex-1 flex flex-col">
          <Header />
          <main className="flex-1 flex items-center justify-center">
            <div className="text-2xl font-bold text-gray-600">Loading dashboard...</div>
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
              <h1 className="text-3xl font-bold">📊 Teacher Dashboard</h1>
              <button
                onClick={() => navigate('/teacher/settings')}
                className="flex items-center gap-2 bg-gray-600 hover:bg-gray-700 text-white px-4 py-2 rounded-lg transition"
              >
                <Settings size={20} />
                Settings
              </button>
            </div>

            {/* Key Metrics */}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4 mb-8">
              <div className="bg-white rounded-lg shadow p-6 hover:shadow-lg transition">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-gray-600 text-sm">Total Students</p>
                    <p className="text-3xl font-bold text-blue-600 mt-2">{stats?.total_students || 0}</p>
                  </div>
                  <Users className="text-blue-400" size={40} />
                </div>
              </div>

              <div className="bg-white rounded-lg shadow p-6 hover:shadow-lg transition">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-gray-600 text-sm">Total Submissions</p>
                    <p className="text-3xl font-bold text-green-600 mt-2">{stats?.total_submissions || 0}</p>
                  </div>
                  <BookOpen className="text-green-400" size={40} />
                </div>
              </div>

              <div className="bg-white rounded-lg shadow p-6 hover:shadow-lg transition cursor-pointer" onClick={() => navigate('/teacher/evaluation-center')}>
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-gray-600 text-sm">Pending Evaluations</p>
                    <p className="text-3xl font-bold text-yellow-600 mt-2">{stats?.pending_evaluations || 0}</p>
                  </div>
                  <BarChart3 className="text-yellow-400" size={40} />
                </div>
              </div>

              <div className="bg-white rounded-lg shadow p-6 hover:shadow-lg transition cursor-pointer" onClick={() => navigate('/teacher/plagiarism')}>
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-gray-600 text-sm">Plagiarism Flags</p>
                    <p className="text-3xl font-bold text-red-600 mt-2">{stats?.plagiarism_flags || 0}</p>
                  </div>
                  <AlertCircle className="text-red-400" size={40} />
                </div>
              </div>

              <div className="bg-white rounded-lg shadow p-6 hover:shadow-lg transition">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-gray-600 text-sm">Class Average</p>
                    <p className="text-3xl font-bold text-purple-600 mt-2">{(stats?.average_score || 0).toFixed(1)}%</p>
                  </div>
                  <TrendingUp className="text-purple-400" size={40} />
                </div>
              </div>
            </div>

            {/* Charts */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
              {/* Class Performance */}
              <div className="bg-white rounded-lg shadow p-6">
                <h3 className="text-lg font-semibold mb-4">Class Performance</h3>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={stats?.class_performance || []}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="name" />
                    <YAxis />
                    <Tooltip />
                    <Legend />
                    <Bar dataKey="average" fill="#8B5CF6" name="Average Score %" />
                  </BarChart>
                </ResponsiveContainer>
              </div>

              {/* Submission Trend */}
              <div className="bg-white rounded-lg shadow p-6">
                <h3 className="text-lg font-semibold mb-4">Submission Trend</h3>
                <ResponsiveContainer width="100%" height={300}>
                  <LineChart data={stats?.class_performance || []}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="date" />
                    <YAxis />
                    <Tooltip />
                    <Legend />
                    <Line type="monotone" dataKey="submissions" stroke="#10B981" strokeWidth={2} name="Submissions" />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Recent Submissions */}
            <div className="bg-white rounded-lg shadow p-6">
              <div className="flex justify-between items-center mb-4">
                <h3 className="text-lg font-semibold">Recent Submissions</h3>
                <button
                  onClick={() => navigate('/teacher/evaluation-center')}
                  className="text-blue-600 hover:text-blue-800 text-sm font-semibold"
                >
                  View All →
                </button>
              </div>

              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead className="bg-gray-100 border-b">
                    <tr>
                      <th className="px-4 py-3 text-left font-semibold text-gray-700">Student</th>
                      <th className="px-4 py-3 text-left font-semibold text-gray-700">Subject</th>
                      <th className="px-4 py-3 text-left font-semibold text-gray-700">Status</th>
                      <th className="px-4 py-3 text-left font-semibold text-gray-700">Submitted</th>
                      <th className="px-4 py-3 text-left font-semibold text-gray-700">Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {stats?.recent_submissions?.map((submission: any) => (
                      <tr key={submission.id} className="border-b hover:bg-gray-50">
                        <td className="px-4 py-3 font-medium">{submission.student_name}</td>
                        <td className="px-4 py-3">{submission.subject}</td>
                        <td className="px-4 py-3">
                          <span className={`px-3 py-1 rounded-full text-xs font-semibold ${
                            submission.status === 'pending' ? 'bg-yellow-100 text-yellow-800' : 'bg-green-100 text-green-800'
                          }`}>
                            {submission.status}
                          </span>
                        </td>
                        <td className="px-4 py-3">{new Date(submission.created_at).toLocaleDateString()}</td>
                        <td className="px-4 py-3">
                          <button className="text-blue-600 hover:text-blue-800 font-semibold">Review</button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Quick Actions */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-8">
              <button
                onClick={() => navigate('/teacher/evaluation-center')}
                className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-4 rounded-lg font-semibold transition flex items-center justify-center gap-2"
              >
                <BookOpen size={20} />
                Review Submissions
              </button>
              <button
                onClick={() => navigate('/teacher/plagiarism')}
                className="bg-red-600 hover:bg-red-700 text-white px-6 py-4 rounded-lg font-semibold transition flex items-center justify-center gap-2"
              >
                <AlertCircle size={20} />
                Check Plagiarism
              </button>
              <button
                onClick={() => navigate('/teacher/analytics')}
                className="bg-purple-600 hover:bg-purple-700 text-white px-6 py-4 rounded-lg font-semibold transition flex items-center justify-center gap-2"
              >
                <TrendingUp size={20} />
                View Analytics
              </button>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
};

export default TeacherDashboard;