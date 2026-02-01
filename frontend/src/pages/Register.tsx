import { useState } from 'react';
import { motion } from 'motion/react';
import { AnimatedBackground } from '../components/AnimatedBackground';
import { Scale, Loader2, UserPlus, ArrowRight, AlertCircle, CheckCircle } from 'lucide-react';

export default function Register({ onRegisterSuccess }: { onRegisterSuccess: () => void }) {
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [email, setEmail] = useState('');
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');

    const validateEmail = (email: string) => {
        return String(email)
            .toLowerCase()
            .match(
                /^(([^<>()[\]\\.,;:\s@"]+(\.[^<>()[\]\\.,;:\s@"]+)*)|.(".+"))@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\])|(([a-zA-Z\-0-9]+\.)+[a-zA-Z]{2,}))$/
            );
    };

    const validateUsername = (username: string) => {
        // Only allow English letters and numbers, no spaces, no accents
        return /^[a-zA-Z0-9]+$/.test(username);
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();

        // Frontend Validation
        if (!validateUsername(username)) {
            setError('Tên đăng nhập chỉ được chứa chữ cái tiếng Anh và số (không dấu, không khoảng trắng).');
            return;
        }
        if (!validateEmail(email)) {
            setError('Email không hợp lệ. Vui lòng kiểm tra lại.');
            return;
        }
        if (password.length < 8) {
            setError('Mật khẩu phải có ít nhất 8 ký tự.');
            return;
        }
        if (password !== confirmPassword) {
            setError('Mật khẩu xác nhận không khớp.');
            return;
        }

        setIsSubmitting(true);
        setError('');
        setSuccess('');

        try {
            const response = await fetch('http://localhost:7860/register', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    username,
                    password,
                    email
                }),
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Registration failed');
            }

            setSuccess('Đăng ký thành công!');
            setTimeout(() => {
                onRegisterSuccess();
            }, 1500);

        } catch (err: any) {
            setError(err.message || 'Có lỗi xảy ra khi đăng ký. (Kiểm tra backend đang chạy chưa?)');
        } finally {
            setIsSubmitting(false);
        }
    };

    return (
        <div className="min-h-screen flex items-center justify-center relative overflow-hidden">
            <AnimatedBackground />

            <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5 }}
                className="w-full max-w-md p-8 relative z-10"
            >
                <div className="bg-white/70 dark:bg-gray-900/60 backdrop-blur-2xl rounded-3xl shadow-2xl border border-white/50 dark:border-gray-700/50 overflow-hidden">
                    <div className="p-8">
                        {/* Header */}
                        <div className="text-center mb-8">
                            <motion.div
                                initial={{ scale: 0 }}
                                animate={{ scale: 1 }}
                                transition={{ type: "spring", stiffness: 200, damping: 15 }}
                                className="w-16 h-16 bg-gradient-to-br from-green-500 to-teal-500 rounded-2xl mx-auto flex items-center justify-center shadow-lg shadow-green-500/20 mb-4 text-white"
                            >
                                <UserPlus size={32} />
                            </motion.div>
                            <h2 className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-gray-900 to-gray-700 dark:from-white dark:to-gray-300">
                                Tạo tài khoản
                            </h2>
                            <p className="text-gray-500 dark:text-gray-400 mt-2 text-sm">
                                Tham gia cộng đồng tư vấn pháp luật AI
                            </p>
                        </div>

                        {/* Form */}
                        <form onSubmit={handleSubmit} className="space-y-4">
                            {error && (
                                <motion.div
                                    initial={{ opacity: 0, x: -10 }}
                                    animate={{ opacity: 1, x: 0 }}
                                    className="p-3 rounded-xl bg-red-50 dark:bg-red-500/10 border border-red-200 dark:border-red-500/20 text-red-600 dark:text-red-400 text-sm flex items-center gap-2"
                                >
                                    <AlertCircle size={16} />
                                    {error}
                                </motion.div>
                            )}
                            {success && (
                                <motion.div
                                    initial={{ opacity: 0, x: -10 }}
                                    animate={{ opacity: 1, x: 0 }}
                                    className="p-3 rounded-xl bg-green-50 dark:bg-green-500/10 border border-green-200 dark:border-green-500/20 text-green-600 dark:text-green-400 text-sm flex items-center gap-2"
                                >
                                    <CheckCircle size={16} />
                                    {success}
                                </motion.div>
                            )}

                            <div className="space-y-4">
                                <div>
                                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5 ml-1">Tên đăng nhập</label>
                                    <input
                                        type="text"
                                        value={username}
                                        onChange={(e) => setUsername(e.target.value)}
                                        className="w-full px-4 py-2.5 rounded-xl border border-gray-200 dark:border-gray-700 bg-white/50 dark:bg-gray-800/50 focus:ring-2 focus:ring-green-500/20 focus:border-green-500 outline-none transition-all dark:text-white"
                                        placeholder="johndoe"
                                        required
                                    />
                                </div>

                                <div>
                                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5 ml-1">Email</label>
                                    <input
                                        type="email"
                                        value={email}
                                        onChange={(e) => setEmail(e.target.value)}
                                        className="w-full px-4 py-2.5 rounded-xl border border-gray-200 dark:border-gray-700 bg-white/50 dark:bg-gray-800/50 focus:ring-2 focus:ring-green-500/20 focus:border-green-500 outline-none transition-all dark:text-white"
                                        placeholder="john@example.com"
                                        required
                                    />
                                </div>

                                <div>
                                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5 ml-1">Mật khẩu</label>
                                    <input
                                        type="password"
                                        value={password}
                                        onChange={(e) => setPassword(e.target.value)}
                                        className="w-full px-4 py-2.5 rounded-xl border border-gray-200 dark:border-gray-700 bg-white/50 dark:bg-gray-800/50 focus:ring-2 focus:ring-green-500/20 focus:border-green-500 outline-none transition-all dark:text-white"
                                        placeholder="••••••••"
                                        required
                                    />
                                </div>

                                <div>
                                    <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1.5 ml-1">Xác nhận mật khẩu</label>
                                    <input
                                        type="password"
                                        value={confirmPassword}
                                        onChange={(e) => setConfirmPassword(e.target.value)}
                                        className="w-full px-4 py-2.5 rounded-xl border border-gray-200 dark:border-gray-700 bg-white/50 dark:bg-gray-800/50 focus:ring-2 focus:ring-green-500/20 focus:border-green-500 outline-none transition-all dark:text-white"
                                        placeholder="••••••••"
                                        required
                                    />
                                </div>
                            </div>

                            <motion.button
                                whileHover={{ scale: 1.02 }}
                                whileTap={{ scale: 0.98 }}
                                type="submit"
                                disabled={isSubmitting}
                                style={{ backgroundColor: '#16a34a', color: '#ffffff' }}
                                className="w-full mt-6 px-4 py-3 font-semibold rounded-xl shadow-lg shadow-green-500/30 hover:bg-green-700 disabled:opacity-70 disabled:cursor-not-allowed flex items-center justify-center gap-2 transition-all"
                            >
                                {isSubmitting ? (
                                    <>
                                        <Loader2 size={18} className="animate-spin" />
                                        <span>Đang đăng ký...</span>
                                    </>
                                ) : (
                                    <>
                                        <span>Đăng ký ngay</span>
                                        <ArrowRight size={18} />
                                    </>
                                )}
                            </motion.button>
                        </form>
                    </div>

                    {/* Footer */}
                    <div className="bg-gray-50/50 dark:bg-gray-800/50 p-4 text-center border-t border-gray-100 dark:border-gray-700/50">
                        <button
                            type="button"
                            onClick={onRegisterSuccess}
                            className="text-sm text-gray-600 dark:text-gray-400 hover:text-green-600 dark:hover:text-green-400 font-medium transition-colors"
                        >
                            Đã có tài khoản? <span className="text-green-600 dark:text-green-400">Đăng nhập ngay</span>
                        </button>
                    </div>
                </div>
            </motion.div>
        </div>
    );
}
