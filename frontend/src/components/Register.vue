<template>
    <div class="login-wrapper">
        <div class="login-container">
            <div class="form-header">
                <h2>用户注册</h2>
                <p>创建您的账号</p>
            </div>
            <form @submit.prevent="handleRegister" class="floating-form">
                <div class="input-group">
                    <input id="username" v-model.trim="registerForm.username" type="text" autocomplete="off" @input="validateInput" required />
                    <label for="username">用户名</label>
                    <span class="highlight"></span>
                </div>
                <div class="input-group">
                    <input id="password" v-model.trim="registerForm.password" type="password" autocomplete="off" @input="validateInput" required />
                    <label for="password">密码</label>
                    <span class="highlight"></span>
                </div>
                <div class="input-group">
                    <input id="confirmPassword" v-model.trim="registerForm.confirmPassword" type="password" autocomplete="off" @input="validateInput" required />
                    <label for="confirmPassword">确认密码</label>
                    <span class="highlight"></span>
                </div>
                <div class="error-message" v-if="errorMsg">{{ errorMsg }}</div>
                <button type="submit" class="submit-btn" :disabled="!isFormValid">
                    <span>注册</span>
                    <i class="arrow-icon"></i>
                </button>
                <div class="form-footer">
                    <span>已有账号？</span>
                    <router-link to="/login">立即登录</router-link>
                </div>
            </form>
        </div>
    </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

const registerForm = reactive({
    username: '',
    password: '',
    confirmPassword: ''
})

const errorMsg = ref('')
const isFormValid = ref(false)

const validateInput = () => {
    const { username, password, confirmPassword } = registerForm
    
    if (!username || !password || !confirmPassword) {
        isFormValid.value = false
        return
    }

    if (password !== confirmPassword) {
        errorMsg.value = '两次输入的密码不一致'
        isFormValid.value = false
        return
    }

    if (password.length < 6) {
        errorMsg.value = '密码长度不能少于6位'
        isFormValid.value = false
        return
    }

    errorMsg.value = ''
    isFormValid.value = true
}

const handleRegister = async () => {
    const xssPattern = /(~|\{|\}|"|'|<|>|\?)/g
    if (xssPattern.test(registerForm.username) || xssPattern.test(registerForm.password)) {
        errorMessage('警告:输入内容包含非法字符');
        return
    }

    try {
        // 注册请求
        const registerResponse = await fetch('http://localhost:5000/api/auth/register', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            body: JSON.stringify({
                username: registerForm.username,
                password: registerForm.password
            })
        });

        const registerData = await registerResponse.json();
        console.log('注册响应:', registerData);

        if (!registerResponse.ok) {
            throw new Error(registerData.message || '注册失败');
        }

        // 注册成功后等待一小段时间再进行登录
        await new Promise(resolve => setTimeout(resolve, 1000));

        // 登录请求（带重试机制）
        let loginAttempts = 0;
        const maxAttempts = 3;
        let loginSuccess = false;
        let lastError = null;

        while (loginAttempts < maxAttempts && !loginSuccess) {
            try {
                const loginResponse = await fetch('http://localhost:5000/api/auth/login', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'Accept': 'application/json'
                    },
                    body: JSON.stringify({
                        username: registerForm.username,
                        password: registerForm.password
                    })
                });

                const loginData = await loginResponse.json();
                console.log(`登录尝试 ${loginAttempts + 1} 响应:`, loginData);

                if (loginResponse.ok && loginData.token) {
                    // 保存token到localStorage
                    localStorage.setItem('token', loginData.token);
                    localStorage.setItem('username', loginData.username);
                    loginSuccess = true;
                    break;
                } else {
                    lastError = new Error(loginData.message || '登录失败');
                    // 等待一段时间后重试
                    await new Promise(resolve => setTimeout(resolve, 1000));
                }
            } catch (error) {
                console.error(`登录尝试 ${loginAttempts + 1} 失败:`, error);
                lastError = error;
                // 等待一段时间后重试
                await new Promise(resolve => setTimeout(resolve, 1000));
            }
            loginAttempts++;
        }

        if (!loginSuccess) {
            throw lastError || new Error('登录重试次数已达上限');
        }

        // 显示成功消息
        errorMessage('注册成功！正在跳转...');

        // 延迟跳转以显示成功消息
        setTimeout(() => {
            router.push('/home');  // 将 '/' 改为 '/home'
        }, 1500);
    } catch (error) {
        console.error('错误详情:', error);
        errorMessage(error.message || '操作失败，请稍后重试');
    }
}

const errorMessage = (text) => {
    errorMsg.value = text
    setTimeout(() => {
        errorMsg.value = ''
    }, 3000)
}

onMounted(() => {
    validateInput()
})
</script>

<style scoped>
.login-wrapper {
    min-height: 93.5vh;
    display: flex;
    align-items: center;
    justify-content: center;
    background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
    padding: 20px;
}

.login-container {
    width: 100%;
    max-width: 480px;
    background: white;
    border-radius: 20px;
    padding: 40px;
    padding-right: 80px;
    box-shadow: 0 15px 35px rgba(0, 0, 0, 0.1);
}

.form-header {
    text-align: center;
    margin-bottom: 40px;
}

.form-header h2 {
    color: #2c3e50;
    font-size: 32px;
    margin-bottom: 10px;
    font-weight: 700;
}

.form-header p {
    color: #95a5a6;
    font-size: 16px;
}

.floating-form .input-group {
    position: relative;
    margin-bottom: 30px;
}

.input-group input {
    width: 100%;
    padding: 15px;
    border: 2px solid #e0e0e0;
    border-radius: 12px;
    font-size: 16px;
    transition: all 0.3s ease;
    background: transparent;
}

.input-group label {
    position: absolute;
    left: 15px;
    top: 50%;
    transform: translateY(-50%);
    background: white;
    padding: 0 5px;
    color: #95a5a6;
    font-size: 16px;
    transition: all 0.3s ease;
    pointer-events: none;
}

.input-group input:focus,
.input-group input:valid {
    border-color: #3498db;
}

.input-group input:focus + label,
.input-group input:valid + label {
    top: 0;
    font-size: 14px;
    color: #3498db;
}

.submit-btn {
    width: 100%;
    padding: 15px;
    margin-left: 15px;
    background: linear-gradient(to right, #3498db, #2980b9);
    color: white;
    border: none;
    border-radius: 12px;
    font-size: 18px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.3s ease;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 10px;
}

.submit-btn:hover {
    transform: translateY(-2px);
    box-shadow: 0 5px 15px rgba(52, 152, 219, 0.3);
}

.submit-btn:disabled {
    background: #95a5a6;
    cursor: not-allowed;
    transform: none;
    box-shadow: none;
}

.arrow-icon {
    border: solid white;
    border-width: 0 2px 2px 0;
    display: inline-block;
    padding: 3px;
    transform: rotate(-45deg);
}

.form-footer {
    text-align: center;
    margin-top: 20px;
    color: #95a5a6;
}

.form-footer a {
    color: #3498db;
    text-decoration: none;
    margin-left: 5px;
    font-weight: 600;
}

.form-footer a:hover {
    text-decoration: underline;
}

.error-message {
    color: #f56c6c;
    font-size: 14px;
    text-align: center;
    margin-bottom: 20px;
}

@media (max-width: 480px) {
    .login-container {
        padding: 20px;
    }
    
    .form-header h2 {
        font-size: 24px;
    }
    
    .input-group input {
        padding: 12px;
    }
}

@media (max-width: 768px) {
    .login-container {
        max-width: 400px;
        padding: 30px;
    }

    .form-header h2 {
        font-size: 28px;
    }

    .form-header p {
        font-size: 14px;
    }
}

@media (max-width: 320px) {
    .login-container {
        padding: 15px;
    }

    .form-header h2 {
        font-size: 20px;
    }

    .input-group {
        margin-bottom: 20px;
    }
}
</style>