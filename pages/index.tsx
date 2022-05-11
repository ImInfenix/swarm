import type { NextPage } from 'next'
import Head from 'next/head'
import Layout from '../components/Layout'
import styles from '../styles/Home.module.css'

const Home: NextPage = () => {
  return (
    <div className={styles.container}>
      <main className={styles.main}>
        <h1 className={styles.title}>Welcome to Swarm</h1>

        <p className={styles.description}>That&apos;s pretty empty right now</p>
      </main>
    </div>
  )
}

export default Home
