import { createRouter, createWebHistory } from "vue-router";
import HomePage from "../components/HomePage.vue";
import NERModule from "../components/NERModule.vue";
import ChatModule from "../components/ChatModule.vue";
import AboutPage from "../components/AboutPage.vue";
import Login from "../components/Login.vue";
import Register from "../components/Register.vue";

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: Login
  },
  {
    path: '/register',
    name: 'Register',
    component: Register
  },
  {
    path: '/home',
    name: 'Home',
    component: HomePage
  },
  {
    path: '/ner',
    name: 'NER',
    component: NERModule
  },
  {
    path: '/chat',
    name: 'Chat',
    component: ChatModule
  },
  {
    path: '/about',
    name: 'About',
    component: AboutPage
  },
  {
    path: '/',
    redirect: '/login'
  }
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

router.beforeEach((to, from, next) => {
  const publicPages = ['/login', '/register'];
  const authRequired = !publicPages.includes(to.path);
  const token = localStorage.getItem('token');

  if (authRequired && !token) {
    next('/login');
  } else {
    next();
  }
});

export default router;