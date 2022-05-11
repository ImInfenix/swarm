import Link from 'next/link'
import styles from '../styles/TopBar.module.css'

export default function TopBar() {
  return (
    <div className="top-bar">
      <div className="top-bar-left">
        <ul className="menu">
          <li className="menu-text">Swarm</li>
          <li>
            <Link href="/">Home</Link>
          </li>
          <li>
            <Link href="/tickets">Tickets</Link>
          </li>
          <li>
            <Link href="/about">About</Link>
          </li>
        </ul>
      </div>
      <div className="top-bar-right">
        <form action="#">
          <ul className="menu">
            <li>
              <input type="search" placeholder="Search" />
            </li>
            <li>
              <button type="submit" className="button">
                Search
              </button>
            </li>
          </ul>
        </form>
      </div>
    </div>
  )
}
