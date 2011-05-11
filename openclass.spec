Summary:	OpenClass is a simple open-source solution for class control
Name:		openclass
Version:	0.0.1
Release:	%mkrel 1
Source0:	%name-%version.tar.bz2
License:	GPLv2
Group:		Networking/Other
Url:		https://github.com/eugeni/openclass
BuildRoot:	%{_tmppath}/%{name}-%{version}-%{release}-buildroot
BuildRequires: python-devel
BuildArch: noarch
Requires:  python
Requires:  pygtk2.0

%description
OpenClass is a simple open-source solution for class control, designed with the
following features in mind:
- small footprint
- light-weight functionality
- minimum of non-essential features

If you already know how italc, bluelab, mythware, iClass and similar solutions
work, you already know what OpenClass is.

%prep
%setup -q

%build

%install
rm -rf $RPM_BUILD_ROOT
%makeinstall_std
%find_lang %name


%clean
rm -rf $RPM_BUILD_ROOT

%files -f %{name}.lang
%defattr(-,root,root) 
%doc README
%_bindir/openclass-student
%_bindir/openclass-teacher
%_datadir/openclass/
%_datadir/applications/openclass-student.desktop
%_datadir/applications/openclass-teacher.desktop
