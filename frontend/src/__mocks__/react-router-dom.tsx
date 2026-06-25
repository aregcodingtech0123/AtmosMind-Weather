import React from 'react';

export const Link = ({
  children,
  to,
  ...rest
}: React.PropsWithChildren<{ to: string } & Record<string, unknown>>) => (
  <a href={to} {...rest}>
    {children}
  </a>
);

export const useNavigate = () => jest.fn();

export const useLocation = () => ({
  pathname: '/',
  search: '',
  hash: '',
  state: null,
  key: 'default',
});

export const MemoryRouter = ({ children }: React.PropsWithChildren) => <>{children}</>;
