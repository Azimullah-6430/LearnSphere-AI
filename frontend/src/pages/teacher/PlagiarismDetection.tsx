import React, { useState, useEffect } from 'react';
import Header from '../../components/Header';
import Sidebar from '../../components/Sidebar';
import { plagiarismService } from '../../services/apiService';
import { AlertTriangle, CheckCircle, User, Mail } from 'lucide-react';
import toast from 'react-hot-toast';

interface StudentDetails {
  id: string;
  name: string;
  email: string;
  roll_number: string;
}

interface PlagiarismFlag {
  submission_id: string;
  student: StudentDetails;
  subject: string;
  plagiarism_score: number;
  matches_count: number;
  created_at: string;
  matches: Array<{
    match_id: string;
    matched_student: StudentDetails;
    similarity: number;
    match_type: string;
  }>;
}

const PlagiarismDetection: React.FC = () => {
  const [flags, setFlags] = useState<PlagiarismFlag[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedFlag, setSelectedFlag] = useState<PlagiarismFlag | null>(null);

  useEffect(() => {
    fetchPlagiarismFlags();
  }, []);

  const fetchPlagiarismFlags = async () => {
    try {
      setLoading(true);
      const data = await plagiarismService.getFlags();
      setFlags(data.flagged_submissions || []);
    } catch (error) {
      toast.error('Failed to load plagiarism flags');
    } finally {
      setLoading(false);
    }
  };

  const getSimilarityColor = (similarity: number) => {
    if (similarity >= 85) return 'text-red-600';
    if (similarity >= 70) return 'text-orange-600';
    return 'text-yellow-600';
  };

  const getMatchTypeBadge = (matchType: string) => {
    if (matchType === 'exact_match') {
      return <span className="px-2 py-1 bg-red-100 text-red-800 rounded text-xs">Exact Match</span>;
    }
    return <span className="px-2 py-1 bg-yellow-100 text-yellow-800 rounded text-xs">Content Similarity</span>;
  };

  if (loading) {
    return (
      <div className="flex h-screen bg-gray-100">
        <Sidebar />
        <div className="flex-1 flex flex-col">
          <Header />
          <main className="flex-1 flex items-center justify-center">
            <div className="text-2xl font-bold text-gray-600">Loading plagiarism data...</div>
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
              <h1 className="text-3xl font-bold">🔍 Advanced Plagiarism Detection</h1>
              <button
                onClick={fetchPlagiarismFlags}
                className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg transition"
              >
                ↻ Refresh
              </button>
            </div>

            {/* Summary */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
              <div className="bg-white rounded-lg shadow p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-gray-600 text-sm">Total Flagged</p>
                    <p className="text-3xl font-bold text-red-600 mt-2">{flags.length}</p>
                  </div>
                  <AlertTriangle className="text-red-400" size={40} />
                </div>
              </div>
              <div className="bg-white rounded-lg shadow p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-gray-600 text-sm">Exact Matches (Renamed PDFs)</p>
                    <p className="text-3xl font-bold text-orange-600 mt-2">
                      {flags.reduce((acc, flag) => acc + flag.matches.filter(m => m.match_type === 'exact_match').length, 0)}
                    </p>
                  </div>
                  <CheckCircle className="text-orange-400" size={40} />
                </div>
              </div>
              <div className="bg-white rounded-lg shadow p-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-gray-600 text-sm">Content Similarities</p>
                    <p className="text-3xl font-bold text-yellow-600 mt-2">
                      {flags.reduce((acc, flag) => acc + flag.matches.filter(m => m.match_type === 'content_similarity').length, 0)}
                    </p>
                  </div>
                  <AlertTriangle className="text-yellow-400" size={40} />
                </div>
              </div>
            </div>

            {/* Flagged Submissions */}
            {flags.length > 0 ? (
              <div className="space-y-6">
                {flags.map((flag) => (
                  <div
                    key={flag.submission_id}
                    className="bg-white rounded-lg shadow-lg overflow-hidden hover:shadow-xl transition"
                  >
                    <div className="bg-red-50 border-l-4 border-red-500 p-6">
                      <div className="flex justify-between items-start mb-4">
                        <div className="flex-1">
                          <h3 className="text-xl font-bold text-red-900 mb-2">
                            🚨 Plagiarism Flag: {flag.student.name}
                          </h3>
                          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                            <div>
                              <p className="text-red-700 font-semibold">Plagiarism Score</p>
                              <p className={`text-2xl font-bold ${getSimilarityColor(flag.plagiarism_score)}`}>
                                {flag.plagiarism_score.toFixed(1)}%
                              </p>
                            </div>
                            <div>
                              <p className="text-red-700 font-semibold">Matches Found</p>
                              <p className="text-2xl font-bold text-red-600">{flag.matches_count}</p>
                            </div>
                            <div>
                              <p className="text-red-700 font-semibold">Subject</p>
                              <p className="text-lg font-semibold text-gray-700">{flag.subject}</p>
                            </div>
                            <div>
                              <p className="text-red-700 font-semibold">Submitted</p>
                              <p className="text-lg font-semibold text-gray-700">
                                {new Date(flag.created_at).toLocaleDateString()}
                              </p>
                            </div>
                          </div>
                        </div>
                        <button
                          onClick={() => setSelectedFlag(selectedFlag?.submission_id === flag.submission_id ? null : flag)}
                          className="bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-lg transition ml-4"
                        >
                          {selectedFlag?.submission_id === flag.submission_id ? 'Hide Details' : 'View Details'}
                        </button>
                      </div>

                      {/* Student Details */}
                      <div className="bg-white rounded p-3 mt-3">
                        <div className="flex items-center gap-4">
                          <div className="flex-1">
                            <div className="flex items-center gap-2 mb-2">
                              <User size={16} className="text-gray-600" />
                              <span className="font-semibold">{flag.student.name}</span>
                              <span className="text-gray-600 text-sm">({flag.student.roll_number})</span>
                            </div>
                            <div className="flex items-center gap-2">
                              <Mail size={16} className="text-gray-600" />
                              <span className="text-sm">{flag.student.email}</span>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Matched Submissions */}
                    {selectedFlag?.submission_id === flag.submission_id && (
                      <div className="p-6 bg-gray-50">
                        <h4 className="font-bold text-lg mb-4 text-gray-900">Matched With:</h4>
                        <div className="space-y-4">
                          {flag.matches.map((match) => (
                            <div
                              key={match.match_id}
                              className="bg-white p-4 rounded-lg border-2 border-orange-200 hover:border-orange-400 transition"
                            >
                              <div className="flex justify-between items-start mb-3">
                                <div className="flex-1">
                                  <h5 className="font-bold text-orange-900 mb-2">
                                    {match.matched_student.name}
                                  </h5>
                                  <div className="grid grid-cols-2 md:grid-cols-3 gap-3 text-sm">
                                    <div>
                                      <p className="text-gray-600">Roll Number</p>
                                      <p className="font-semibold">{match.matched_student.roll_number}</p>
                                    </div>
                                    <div>
                                      <p className="text-gray-600">Email</p>
                                      <p className="font-semibold text-xs">{match.matched_student.email}</p>
                                    </div>
                                    <div>
                                      <p className="text-gray-600">Similarity</p>
                                      <p className={`text-lg font-bold ${getSimilarityColor(match.similarity)}`}>
                                        {match.similarity.toFixed(1)}%
                                      </p>
                                    </div>
                                  </div>
                                </div>
                                <div className="ml-4">
                                  {getMatchTypeBadge(match.match_type)}
                                </div>
                              </div>

                              {/* Student Details Card */}
                              <div className="bg-blue-50 rounded p-3 mt-3">
                                <p className="text-xs font-semibold text-blue-900 mb-2">MATCHED STUDENT DETAILS:</p>
                                <div className="grid grid-cols-2 gap-2 text-xs">
                                  <div>
                                    <span className="font-semibold">Name:</span> {match.matched_student.name}
                                  </div>
                                  <div>
                                    <span className="font-semibold">Roll:</span> {match.matched_student.roll_number}
                                  </div>
                                  <div className="col-span-2">
                                    <span className="font-semibold">Email:</span> {match.matched_student.email}
                                  </div>
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>

                        {/* Action Buttons */}
                        <div className="mt-6 flex gap-4">
                          <button className="flex-1 bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-lg transition font-semibold">
                            ⛔ Block Both Students
                          </button>
                          <button className="flex-1 bg-orange-600 hover:bg-orange-700 text-white px-4 py-2 rounded-lg transition font-semibold">
                            ⚠️ Send Warning
                          </button>
                          <button className="flex-1 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-lg transition font-semibold">
                            📋 Generate Report
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <div className="bg-white rounded-lg shadow p-12 text-center">
                <CheckCircle className="mx-auto text-green-500 mb-4" size={48} />
                <h3 className="text-2xl font-bold text-gray-900 mb-2">No Plagiarism Detected</h3>
                <p className="text-gray-600">All submissions are original and verified. Great academic integrity!</p>
              </div>
            )}
          </div>
        </main>
      </div>
    </div>
  );
};

export default PlagiarismDetection;