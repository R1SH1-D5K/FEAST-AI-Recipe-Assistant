"use client"

import Image from "next/image"

interface HeaderProps {
  onHomeClick: () => void
}

export function Header({ onHomeClick }: HeaderProps) {
  return (
    <header className="fixed top-0 left-0 z-50 p-4">
      <button onClick={onHomeClick} className="transition-opacity hover:opacity-80" aria-label="Return to home">
        <Image src="/feast-logo-full.png" alt="Feast" width={130} height={130} className="opacity-90 w-[130px] h-[130px]" />
      </button>
    </header>
  )
}
